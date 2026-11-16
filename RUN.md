# AegisQuant — Hướng dẫn chạy toàn bộ dự án

Tài liệu này hướng dẫn chạy Backend FastAPI, Worker, Frontend Vue/Vite và các
kiểm thử của AegisQuant. Mặc định hệ thống chạy **DRY_RUN**, không gửi lệnh thật.

## 1. Kiến trúc khi chạy

```text
Browser (Vue/Vite hoặc frontend/dist)
              │ HTTP + WebSocket
              ▼
      FastAPI: http://localhost:8000
              │
              ├── Binance public market data
              ├── deterministic indicators / guardrails
              ├── Gemini agents (chỉ khi đã cấu hình)
              ├── Zalo OA alerts (tùy chọn)
              └── Worker giao dịch
```

Các file chính:

- Backend API: `src/api/server.py`
- Pipeline: `src/main.py`
- Exchange orders: `src/execution/order_manager.py`
- Zalo OA: `src/notifications/zalo_oa.py`
- Frontend: `frontend/src/App.vue`
- Docker: `Dockerfile`, `docker-compose.yml`

## 2. Yêu cầu

- Docker Desktop đang chạy, hoặc:
  - Python 3.11+
  - Node.js 18+
  - npm
- Không cần API key để chạy DRY_RUN hoặc xem dashboard mô phỏng.

## 3. Cấu hình môi trường

Tạo file `.env` từ template:

```powershell
Copy-Item .env.example .env
```

Giữ cấu hình an toàn mặc định:

```env
TRADING_MODE=DRY_RUN
```

Các biến quan trọng:

```env
# Exchange
TRADING_MODE=DRY_RUN
BINANCE_API_KEY=
BINANCE_SECRET=
WORKER_INTERVAL_SECONDS=900

# Gemini
GEMINI_API_KEY=

# Zalo Official Account
ZALO_APP_ID=
ZALO_SECRET_KEY=
ZALO_REFRESH_TOKEN=
ZALO_ADMIN_USER_ID=
ZALO_TOKEN_PATH=data/zalo_tokens.json
```

Không commit `.env`, API keys, refresh token hoặc `data/zalo_tokens.json`.

## 4. Cách nhanh nhất: chạy toàn bộ bằng Docker

Từ thư mục gốc repository:

```powershell
docker compose build
docker compose up -d
docker compose ps
```

Mở dashboard:

```text
http://localhost:8000
```

Kiểm tra API:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/status
```

Xem log:

```powershell
docker compose logs -f backend worker
```

Dừng hệ thống:

```powershell
docker compose down
```

Compose chạy hai service:

- `backend`: FastAPI + frontend build, port `8000`
- `worker`: vòng lặp worker nền, dùng chung thư mục `data/`

## 5. Chạy Backend local

Tạo virtual environment và cài dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Chạy API:

```powershell
python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Mở:

```text
http://localhost:8000
```

Chạy worker ở terminal thứ hai:

```powershell
python -m src.worker
```

## 6. Chạy Frontend riêng bằng Vite

Backend vẫn phải chạy ở port `8000`.

```powershell
Set-Location frontend
npm install
npm run dev
```

Mở URL Vite hiển thị trong terminal, thường là:

```text
http://localhost:5173
```

Frontend tự dùng Backend tại `http://localhost:8000` khi chạy trên Vite.

Nếu frontend được deploy riêng lên Vercel, tạo Environment Variables:

```env
VITE_API_BASE_URL=https://api.phmdanh.id.vn
VITE_API_WS_URL=wss://api.phmdanh.id.vn/ws/stream
```

`api.phmdanh.id.vn` phải trỏ tới backend FastAPI public; Vercel chỉ phục vụ
frontend, không chạy worker giao dịch lâu dài.

Build production frontend:

```powershell
Set-Location frontend
npm run build
```

Sau đó quay về root trước khi chạy Docker:

```powershell
Set-Location ..
docker compose build
docker compose up -d
```

## 7. Chế độ vận hành

### DRY_RUN — khuyến nghị khi bắt đầu

```env
TRADING_MODE=DRY_RUN
```

- Không gửi lệnh Binance.
- Có thể dùng dashboard, preset và kill switch.
- Không cần Binance API key.

### TESTNET — chỉ bật sau khi đã kiểm tra DRY_RUN

```env
TRADING_MODE=TESTNET
BINANCE_API_KEY=<binance-testnet-key>
BINANCE_SECRET=<binance-testnet-secret>
```

Sau đó khởi động lại:

```powershell
docker compose up -d --build
```

`order_manager.py` sẽ:

1. Bật Binance sandbox.
2. Ép `isolated` margin.
3. Giới hạn leverage tối đa `10x`.
4. Đặt entry cùng Stop-Loss và Take-Profit reduce-only.

Không dùng API key live khi chưa hoàn tất tối thiểu 14 ngày Testnet.

## 8. Các thao tác trên dashboard

- `LIVE SYNC`: lấy market snapshot từ Binance public API.
- `long_approved`: mô phỏng một kèo được duyệt.
- `short_rejected`: mô phỏng kèo bị Devil's Advocate từ chối.
- `macro_lock`: mô phỏng circuit breaker khi có tin vĩ mô.
- `PAPER TRADING`: chuyển giữa DRY_RUN và TESTNET qua API.
- `KILL SWITCH`: khóa/mở luồng giao dịch.

Frontend sử dụng các endpoint:

```text
GET  /api/status
GET  /api/portfolio
GET  /api/history
GET  /api/market/live?timeframe=1h&limit=120
POST /api/sync-live
POST /api/mode?mode=DRY_RUN
POST /api/simulate/{preset}
POST /api/kill-switch?enabled=true
WS   /ws/stream
```

## 9. Kiểm thử

Backend:

```powershell
python -m pytest -q
```

Frontend:

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

KPI audit:

```powershell
python scripts/evaluate_kpi.py data/audit_log.jsonl
```

Nếu chưa có audit log, script trả về các KPI bằng `0.0`; đây là trạng thái
chưa chạy dry-run, không phải kết quả đạt KPI.

## 10. Kiểm tra WebSocket

WebSocket contract đầy đủ nằm tại `docs/WS_STREAM_CONTRACT.json`.

Payload tối thiểu:

```json
{
  "market_snapshot": {
    "symbol": "BTC/USDT:USDT",
    "price": 0.0,
    "entry": null,
    "sl": null,
    "tp": null,
    "liquidation_price": null,
    "rr_ratio": null
  },
  "agent_debate_stream": [],
  "system_status": {
    "gatekeeper": false,
    "remaining_daily_quota_estimate": null,
    "kill_switch": false
  }
}
```

## 11. Troubleshooting

### Docker daemon không chạy

Mở Docker Desktop, chờ trạng thái engine sẵn sàng rồi kiểm tra:

```powershell
docker info
```

### Port 8000 đã được sử dụng

```powershell
docker compose down
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

Hoặc đổi port host trong `docker-compose.yml`, ví dụ `"8080:8000"`.

### Frontend không nhận WebSocket

Kiểm tra Backend đang chạy tại `http://localhost:8000`, sau đó refresh trang.
Khi mở frontend bằng Vite, dùng `ws://localhost:8000/ws/stream`; khi mở
dashboard từ FastAPI, dùng cùng origin.

### Zalo không gửi được

Kiểm tra bốn biến `ZALO_*`, quyền OA, `ZALO_ADMIN_USER_ID` và file:

```text
data/zalo_tokens.json
```

Không đưa token vào log hoặc commit.
