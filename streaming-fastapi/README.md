# streaming-fastapi（Python 笔试题）

FastAPI 流式 API demo：一个 async generator 驱动三种流式响应，并附带浏览器演示页。

## 运行

```bash
pip install -r requirements.txt
python main.py                    # 或 uvicorn main:app --reload
# 打开 http://127.0.0.1:8000
```

## 接口

| 接口 | 类型 | 说明 |
|---|---|---|
| `GET /api/stream?prompt=...` | `text/plain` chunked | 模拟 LLM 逐 token 输出（打字机效果） |
| `GET /api/sse?count=10` | `text/event-stream` | SSE 结构化进度事件，最后发 `done` 事件 |
| `GET /api/stream-file?mb=1` | `application/octet-stream` | 64KB 分块下载 1MB 数据，可校验块完整性 |
| `GET /` | HTML | 演示页：fetch + ReadableStream / EventSource 可视化消费前两种流 |

## 快速验证

```bash
# 首字节时间远小于总耗时，即为真流式
curl -s -N -o /dev/null -w "first-byte %{time_starttransfer}s | total %{time_total}s\n" \
  "http://127.0.0.1:8000/api/stream"
# 实测：first-byte 0.02s | total 6.5s

# 查看原始 SSE 事件
curl -N "http://127.0.0.1:8000/api/sse?count=3"

# 分块下载并校验大小
curl -s -o demo.bin "http://127.0.0.1:8000/api/stream-file?mb=1"
```

## 实现要点

- **核心机制**：`StreamingResponse` 接收一个 **async generator**，uvicorn 以 chunked
  transfer 编码逐块写出，客户端无需等整个响应完成。
- **两种消费方式**：文本流用 `fetch` + `ReadableStream` 手动读块（演示页面板 1）；
  SSE 用浏览器原生 `EventSource` 自动解析 `event:`/`data:`（演示页面板 2）。
- **穿透代理缓冲**：响应头带 `X-Accel-Buffering: no` + `Cache-Control: no-cache`，
  避免 nginx 等反向代理把流缓冲成"一次性返回"。
- **SSE 规范格式**：`id` / `event` / `data` 三字段 + 空行分隔，结束发 `done` 事件，
  客户端收到后 `EventSource.close()` 防止自动重连。
- **二进制流**：固定 64KB 分块，每块以块号重复填充，接收端可逐块校验完整性。

## 提交到 GitHub

```bash
git init
git add .
git commit -m "feat: fastapi streaming api demo (chunked/sse/binary)"
git remote add origin https://github.com/<你的用户名>/streaming-fastapi.git
git push -u origin main
```
