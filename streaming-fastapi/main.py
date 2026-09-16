"""FastAPI streaming demo.

演示 FastAPI 的三种流式响应：

- GET /api/stream       chunked 文本流：模拟大模型逐字输出（打字机效果）
- GET /api/sse          Server-Sent Events：结构化 JSON 事件流
- GET /api/stream-file  二进制流：分块下载一个内存生成的"大文件"
- GET /                 浏览器演示页，可视化查看前两种流的效果

Run:
    python main.py                 # http://127.0.0.1:8000
    uvicorn main:app --reload      # 开发模式
"""

import asyncio
import json
import time

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI(
    title="FastAPI Streaming Demo",
    description="Chunked streaming / SSE / binary streaming demo",
    version="1.0.0",
)

REPLY_TEXT = (
    "你好！这是一个 FastAPI 流式响应的演示。"
    "服务端使用 async generator 逐块产出文本，"
    "浏览器通过 fetch + ReadableStream 边接收边渲染，"
    "所以你能看到文字逐渐出现，就像 ChatGPT 的打字机效果。"
    "背后并没有真正的大模型，只有 asyncio.sleep 模拟的生成延迟。"
)

# 让流式效果肉眼可见的节奏
CHAR_DELAY = 0.04       # /api/stream 每个字符的间隔
CHUNK_SIZE = 3          # 每个 chunk 包含的字符数
SSE_EVENT_DELAY = 0.4   # /api/sse 每个事件的间隔
FILE_CHUNK_SIZE = 64 * 1024
FILE_TOTAL_SIZE = 1024 * 1024

# 告诉反向代理不要缓冲此响应（nginx 默认会缓冲，导致流式变"一次性"）
NO_BUFFER_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@app.get("/api/stream")
async def stream_text(prompt: str = Query(default="streaming", description="会被回显在流的开头")):
    """Chunked 文本流：模拟 LLM 逐 token 输出。"""
    async def generator():
        text = f"收到提示词：{prompt}。\n\n" + REPLY_TEXT
        for i in range(0, len(text), CHUNK_SIZE):
            yield text[i:i + CHUNK_SIZE]
            await asyncio.sleep(CHAR_DELAY * CHUNK_SIZE)

    return StreamingResponse(
        generator(),
        media_type="text/plain; charset=utf-8",
        headers=NO_BUFFER_HEADERS,
    )


@app.get("/api/sse")
async def stream_sse(count: int = Query(default=10, ge=1, le=100)):
    """Server-Sent Events：每 0.4s 推送一个 JSON 进度事件，最后发 done 事件。"""
    async def generator():
        start = time.time()
        for i in range(1, count + 1):
            event = {
                "index": i,
                "total": count,
                "percent": round(i / count * 100),
                "elapsed_ms": round((time.time() - start) * 1000),
                "message": f"处理进度 {i}/{count}",
            }
            yield (
                f"id: {i}\n"
                f"event: progress\n"
                f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            )
            await asyncio.sleep(SSE_EVENT_DELAY)
        yield "event: done\ndata: {\"status\": \"finished\"}\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={**NO_BUFFER_HEADERS, "Connection": "keep-alive"},
    )


@app.get("/api/stream-file")
async def stream_file(mb: float = Query(default=1.0, gt=0, le=100)):
    """二进制流：分块发送 mb 兆的伪随机数据，演示文件下载场景。"""
    total = int(mb * FILE_TOTAL_SIZE)

    async def generator():
        sent = 0
        seq = 0
        while sent < total:
            size = min(FILE_CHUNK_SIZE, total - sent)
            # 生成一段可校验的数据块：块号重复填充，接收方可验证完整性
            chunk = (str(seq) * size)[:size].encode()
            yield chunk
            sent += size
            seq += 1

    return StreamingResponse(
        generator(),
        media_type="application/octet-stream",
        headers={
            **NO_BUFFER_HEADERS,
            "Content-Disposition": 'attachment; filename="stream-demo.bin"',
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    """浏览器演示页。"""
    return INDEX_HTML


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FastAPI Streaming Demo</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0d1117; color: #e6edf3;
    display: flex; flex-direction: column; align-items: center;
    padding: 40px 16px; min-height: 100vh;
  }
  h1 { font-size: 26px; margin-bottom: 6px; }
  .sub { color: #8b949e; font-size: 14px; margin-bottom: 28px; }
  .panel {
    width: min(760px, 100%); background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 20px; margin-bottom: 24px;
  }
  .panel h2 { font-size: 16px; margin-bottom: 4px; }
  .panel .desc { color: #8b949e; font-size: 13px; margin-bottom: 14px; }
  .row { display: flex; gap: 10px; margin-bottom: 12px; }
  input {
    flex: 1; background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    color: #e6edf3; padding: 9px 12px; font-size: 14px; outline: none;
  }
  input:focus { border-color: #2f81f7; }
  button {
    background: #238636; color: #fff; border: none; border-radius: 8px;
    padding: 9px 18px; font-size: 14px; cursor: pointer;
  }
  button:hover { filter: brightness(1.15); }
  button:disabled { opacity: .5; cursor: not-allowed; }
  button.secondary { background: #21262d; border: 1px solid #30363d; }
  .out {
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    padding: 14px; min-height: 120px; font-size: 14px; line-height: 1.7;
    white-space: pre-wrap; word-break: break-word;
  }
  .out.mono { font-family: Consolas, monospace; font-size: 13px; max-height: 220px; overflow-y: auto; }
  .cursor { display: inline-block; width: 8px; height: 16px; background: #2f81f7;
            animation: blink 1s step-end infinite; vertical-align: text-bottom; }
  @keyframes blink { 50% { opacity: 0; } }
  .status { font-size: 12px; color: #8b949e; margin-top: 8px; min-height: 16px; }
  code { color: #79c0ff; }
</style>
</head>
<body>
  <h1>FastAPI Streaming Demo</h1>
  <div class="sub">chunked 文本流 · Server-Sent Events · 分块文件下载</div>

  <div class="panel">
    <h2>1. 模拟 LLM 逐字输出 <code>GET /api/stream</code></h2>
    <div class="desc">fetch + ReadableStream 逐块读取 text/plain，打字机效果</div>
    <div class="row">
      <input id="prompt" value="用一句话介绍流式接口" />
      <button id="btnStream" onclick="startStream()">开始流式请求</button>
    </div>
    <div class="out"><span id="llmOut"></span><span id="cursor" class="cursor" style="display:none"></span></div>
    <div class="status" id="llmStatus"></div>
  </div>

  <div class="panel">
    <h2>2. Server-Sent Events <code>GET /api/sse</code></h2>
    <div class="desc">EventSource 接收结构化进度事件，适合任务进度推送</div>
    <div class="row">
      <button id="btnSse" onclick="startSse()">开始 SSE（10 个事件）</button>
      <button class="secondary" onclick="stopSse()">停止</button>
    </div>
    <div class="out mono" id="sseOut">等待开始…</div>
    <div class="status" id="sseStatus"></div>
  </div>

<script>
const llmOut = document.getElementById('llmOut');
const cursor = document.getElementById('cursor');
const llmStatus = document.getElementById('llmStatus');

async function startStream() {
  const btn = document.getElementById('btnStream');
  btn.disabled = true;
  llmOut.textContent = '';
  cursor.style.display = 'inline-block';
  llmStatus.textContent = '连接中…';
  const t0 = performance.now();
  try {
    const res = await fetch('/api/stream?prompt=' +
        encodeURIComponent(document.getElementById('prompt').value));
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let firstChunkMs = null;
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      if (firstChunkMs === null) {
        firstChunkMs = (performance.now() - t0).toFixed(0);
        llmStatus.textContent = '首块到达：' + firstChunkMs + ' ms，接收中…';
      }
      llmOut.textContent += decoder.decode(value, {stream: true});
    }
    llmStatus.textContent = '完成：首块 ' + firstChunkMs +
        ' ms，总耗时 ' + ((performance.now() - t0) / 1000).toFixed(1) + ' s';
  } catch (e) {
    llmStatus.textContent = '出错：' + e;
  } finally {
    cursor.style.display = 'none';
    btn.disabled = false;
  }
}

let es = null;
const sseOut = document.getElementById('sseOut');
const sseStatus = document.getElementById('sseStatus');

function startSse() {
  stopSse();
  sseOut.textContent = '';
  document.getElementById('btnSse').disabled = true;
  es = new EventSource('/api/sse?count=10');
  es.addEventListener('progress', e => {
    const d = JSON.parse(e.data);
    sseOut.textContent += `[${e.lastEventId}] ${d.percent}%  ${d.message}  (elapsed ${d.elapsed_ms}ms)\\n`;
    sseOut.scrollTop = sseOut.scrollHeight;
  });
  es.addEventListener('done', () => {
    sseStatus.textContent = '服务端已发送 done 事件，连接关闭';
    stopSse();
  });
  es.onerror = () => { sseStatus.textContent = '连接中断'; stopSse(); };
}

function stopSse() {
  if (es) { es.close(); es = null; }
  document.getElementById('btnSse').disabled = false;
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
