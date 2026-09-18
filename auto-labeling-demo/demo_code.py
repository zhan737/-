"""Auto Labeling with an LLM: 用 Qwen2.5-0.5B-Instruct 为 ChnSentiCorp 自动标注情感。

流程:
  1. 读取带人工标注的公开数据集 ChnSentiCorp（测试集，parquet 格式）
  2. 分层抽样 n 条（保持正负样本比例，固定随机种子，结果可复现）
  3. 对每条文本构造受限标签提示词，调用本地 LLM（CPU 推理，无需 API Key）
  4. 解析模型输出为标签（失败自动重试一次），与人工标注对比
  5. 输出 results.csv（逐条对照）+ 终端准确率/混淆统计

运行:
    python demo_code.py                      # 默认标注 60 条
    python demo_code.py --n 100 --out results.csv
    # 国内网络首次下载模型请设置环境变量 HF_ENDPOINT=https://hf-mirror.com
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from pathlib import Path

LABELS = ["正面", "负面"]
LABEL_ALIASES = {
    "正面": "正面", "positive": "正面", "pos": "正面", "1": "正面",
    "负面": "负面", "negative": "负面", "neg": "负面", "0": "负面",
}
DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_DATA = Path(__file__).parent / "chnsenticorp_test.parquet"

SYSTEM_PROMPT = "你是一名严谨的数据标注员，负责判断中文评论的情感倾向。"
USER_TEMPLATE = (
    "请判断下面这条评论的情感倾向。\n"
    "只允许输出以下标签之一：{labels}。\n"
    '只输出一个 JSON 对象，格式：{{"label": "正面"}} 或 {{"label": "负面"}}，'
    "不要输出任何其他内容。\n\n"
    "评论：{text}"
)


def load_dataset(path: Path):
    """读取 parquet，返回 [(text, gold_label), ...]，gold 统一映射为 正面/负面。"""
    import pandas as pd

    df = pd.read_parquet(path)
    col_text = next(c for c in ("text", "review", "sentence") if c in df.columns)
    col_label = next(c for c in ("label", "sentiment") if c in df.columns)
    pairs = []
    for _, row in df.iterrows():
        text = str(row[col_text]).strip()
        gold = LABEL_ALIASES.get(str(row[col_label]).strip().lower())
        if text and gold:
            pairs.append((text, gold))
    return pairs


def stratified_sample(pairs, n, seed=42):
    """分层抽样：每个类别各取 n/2 条，n 为奇数时正类多一条。"""
    rng = random.Random(seed)
    per_class = {lab: [t for t, g in pairs if g == lab] for lab in LABELS}
    half = n - n // 2
    picked = []
    for lab, k in (("正面", half), ("负面", n - half)):
        pool = per_class[lab][:]
        rng.shuffle(pool)
        picked.extend((t, lab) for t in pool[:k])
    rng.shuffle(picked)
    return picked


def build_messages(text):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(
            labels="、".join(LABELS), text=text)},
    ]


def parse_label(raw: str):
    """从模型输出中鲁棒地提取标签；失败返回 None。"""
    m = re.search(r"\{[^{}]*\}", raw, flags=re.S)
    candidates = []
    if m:
        try:
            candidates.append(json.loads(m.group(0)).get("label", ""))
        except json.JSONDecodeError:
            pass
    candidates.append(raw)  # 兜底：整段输出里找标签词
    for cand in candidates:
        low = str(cand).lower()
        for key, label in LABEL_ALIASES.items():
            if key in low:
                return label
    return None


class LocalLLM:
    """本地 CPU 推理（无需 API Key）。首次运行会自动下载约 1GB 模型权重。"""

    def __init__(self, model_id: str):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(os.cpu_count() or 4)
        self.torch = torch
        print(f"[model] loading {model_id} (CPU) ...", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        try:  # transformers >= 4.56 用 dtype，旧版用 torch_dtype
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, dtype="auto", low_cpu_mem_usage=True)
        except TypeError:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, torch_dtype="auto", low_cpu_mem_usage=True)
        self.model.eval()
        print("[model] ready", flush=True)

    def chat(self, messages, max_new_tokens=16):
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with self.torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens, do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def label_one(llm, text):
    """标注单条：解析失败则带错误反馈重试一次。"""
    raw = llm.chat(build_messages(text))
    label = parse_label(raw)
    if label is None:
        retry = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(labels="、".join(LABELS), text=text)},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "你的输出不符合要求。只输出 JSON：{\"label\": \"正面\"} 或 {\"label\": \"负面\"}。"},
        ]
        raw = llm.chat(retry)
        label = parse_label(raw)
    return label, raw


def main():
    ap = argparse.ArgumentParser(description="LLM auto-labeling demo")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="ChnSentiCorp parquet 路径")
    ap.add_argument("--model", default=os.environ.get("AUTO_LABEL_MODEL", DEFAULT_MODEL))
    ap.add_argument("--n", type=int, default=60, help="标注条数（分层抽样）")
    ap.add_argument("--out", default="results.csv", help="输出 CSV 路径")
    args = ap.parse_args()

    pairs = load_dataset(Path(args.data))
    print(f"[data] 数据集共 {len(pairs)} 条，分层抽样 {args.n} 条", flush=True)
    sample = stratified_sample(pairs, args.n)

    llm = LocalLLM(args.model)

    rows = []
    t_start = time.time()
    for i, (text, gold) in enumerate(sample, 1):
        t0 = time.time()
        label, raw = label_one(llm, text)
        rows.append({
            "index": i, "text": text, "gold_label": gold,
            "model_label": label or "解析失败", "raw_output": raw,
            "correct": str(label == gold),
            "latency_s": round(time.time() - t0, 2),
        })
        print(f"[{i:>3}/{len(sample)}] gold={gold} model={label or '?'} "
              f"({time.time() - t0:.1f}s) {text[:24]}", flush=True)

    # 写出逐条结果
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # 统计
    done = [r for r in rows if r["model_label"] in LABELS]
    correct = [r for r in done if r["correct"] == "True"]
    acc = len(correct) / len(done) if done else 0.0
    lat = sorted(r["latency_s"] for r in done)
    print("\n===== 汇总 =====")
    print(f"标注完成: {len(done)}/{len(rows)}（解析失败 {len(rows) - len(done)} 条）")
    print(f"准确率 vs 人工标注: {len(correct)}/{len(done)} = {acc:.1%}")
    for lab in LABELS:
        tp = sum(1 for r in correct if r["gold_label"] == lab)
        total = sum(1 for r in done if r["gold_label"] == lab)
        pred = sum(1 for r in done if r["model_label"] == lab)
        print(f"  {lab}: 人工 {total} 条，召回 {tp}/{total}，模型判为 {lab} 共 {pred} 条")
    if lat:
        print(f"单条延迟: 中位 {lat[len(lat)//2]:.1f}s / 最快 {lat[0]:.1f}s / 最慢 {lat[-1]:.1f}s")
    print(f"总耗时 {(time.time() - t_start) / 60:.1f} min，结果已写入 {args.out}")

    # 打印 5 个示例（含错误样例优先，便于分析）
    print("\n===== 示例输出 =====")
    wrong = [r for r in rows if r["correct"] == "False"][:3]
    right = [r for r in rows if r["correct"] == "True"][:2]
    for r in wrong + right:
        print(f"- [{r['gold_label']}→{r['model_label']}] {r['text'][:40]} | 模型原始输出: {r['raw_output'][:40]}")


if __name__ == "__main__":
    main()
