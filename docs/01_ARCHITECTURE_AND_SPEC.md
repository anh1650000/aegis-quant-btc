# 01_ARCHITECTURE_AND_SPEC - Kiến trúc Hệ thống (Google AI Pro Edition)

## 1. Tổng quan Kiến trúc (Hybrid Event-Driven Pipeline)
Hệ thống giao dịch tự động cặp **BTC/USDT Perpetual Futures** được thiết kế theo mô hình **Lọc phễu đa tầng (Cascading Gatekeeper)** nhằm tận dụng tối đa sức mạnh của gói **Google AI Pro** (`Gemini 4 Hydrogen` + `Gemini 4 Argon`) mà vẫn kiểm soát chặt chẽ lượng token tiêu thụ.

```
[Tầng 1: Data & Feature Engine (Python/CCXT)] ---> (0 Token - Chạy mỗi 15m/1h)
                     │
                     ▼
[Tầng 2: Predictive ML & Gatekeeper (LightGBM)] ---> (0 Token - Lọc 85% nhiễu)
                     │ (Chỉ kích hoạt khi Prob > 65% & Có hợp lưu kỹ thuật)
                     ▼
[Tầng 3: Dual-Model Reasoning (Google AI Pro)]
 ├── News Cache Worker: Gemini 4 Hydrogen (Chạy nền mỗi 2h + Google Search)
 ├── Analyst Role: Gemini 4 Argon (Đọc Minified JSON & Tìm điểm vào)
 └── Devil's Advocate Role: Gemini 4 Argon (Phản biện rủi ro & Phủ quyết)
                     │
                     ▼
[Tầng 4: Deterministic Risk Guardrails & Execution] ---> (Python Hard-coded)
```

---

## 2. Chi tiết từng Tầng xử lý

### Tầng 1: Deterministic Data & Feature Engineering (0 Token)
* **Thư viện:** `ccxt.async_support`, `pandas-ta`, `numpy`.
* **Dữ liệu thu thập (Public Endpoints):**
  * Nến OHLCV đa khung thời gian: `15m` (tìm điểm vào), `1h` (xu hướng ngắn), `4h` (xu hướng chính).
  * Dữ liệu phái sinh: `Funding Rate`, `Open Interest (OI)`, `Long/Short Ratio`.
* **Nén dữ liệu:** Toàn bộ chỉ báo (EMA 20/50/200, RSI 14, ATR 14, Bollinger Bands, Volume Ratio) được tính bằng Python và đóng gói thành **Minified JSON** (`~350 tokens/lần gọi`).

### Tầng 2: Predictive ML & Gatekeeper Engine (0 Token)
* **Mô hình:** `LightGBM` hoặc `CatBoost` huấn luyện trên dữ liệu lịch sử BTC/USDT 3 năm gần nhất.
* **Cơ chế Cổng gác (Gatekeeper):**
  * Hệ thống chạy ngầm hoàn toàn bằng Python trên máy local/VPS.
  * Chỉ mở cổng gọi API của **Gemini 4 Argon** khi thỏa mãn đồng thời:
    1. Xác suất dự báo biến động từ mô hình ML `>= 0.65`.
    2. Giá nằm gần vùng hỗ trợ/kháng cự động (EMA/Bollinger Bands) hoặc có biến động khối lượng đột biến (`Volume > 1.5x MA20`).
  * *Hiệu quả:* Giảm số lần gọi LLM từ ~96 lần/ngày xuống còn **3–6 lần/ngày** (chỉ gọi khi thực sự có cơ hội giao dịch).

### Tầng 3: Dual-Model Reasoning (Tối ưu cho Google AI Pro)
Thay vì dùng model `Carbon` đắt đỏ, hệ thống sử dụng chiến thuật **Role-Playing trên Gemini 4 Argon** kết hợp với **Gemini 4 Hydrogen**:
1. **News & Macro Sentinel (`gemini-4-hydrogen` + Google Search Tool):**
   * Chạy độc lập theo lịch trình **2 giờ/lần** (không chạy theo nến) để tiết kiệm quota và lưu kết quả vào file `cache/macro_sentiment.json`.
   * Quét tin vĩ mô (CPI, FOMC, lãi suất Fed) và tin tức crypto nóng hổi để gắn cờ cảnh báo sự kiện (`HIGH_IMPACT_EVENT`).
2. **Lead Quantitative Analyst (`gemini-4-argon` - Lượt 1):**
   * Đọc `Minified JSON` từ Tầng 1, xác suất từ Tầng 2 và file `cache/macro_sentiment.json`.
   * Đề xuất kịch bản giao dịch (`LONG`, `SHORT`, hoặc `HOLD`) kèm vùng giá `Entry`, `Stop-Loss`, `Take-Profit` dựa trên bội số ATR.
3. **Risk Manager / Devil's Advocate (`gemini-4-argon` - Lượt 2):**
   * Nhận đề xuất của Lượt 1 cùng dữ liệu Funding Rate và Open Interest.
   * Đóng vai người phản biện cực đoan, tìm mọi lý do khiến lệnh có thể bị quét Stop-Loss (Long/Short Squeeze, phân kỳ yếu, sắp ra tin). Có quyền phủ quyết (`REJECT`) nếu rủi ro bất đối xứng.

### Tầng 4: Deterministic Execution & Risk Guardrails (0 Token)
* **Thư viện:** `pydantic`, `ccxt`.
* **Chức năng:**
  * Kiểm duyệt đầu ra JSON của Argon qua các hàm kiểm tra toán học cứng (Hard Guardrails).
  * Tự động tính toán `Position Size` (khối lượng BTC) dựa trên số tiền rủi ro tối đa (`1.5%` tài khoản).
  * Đẩy lệnh trực tiếp lên sàn với chế độ `Isolated Margin` và gắn `Stop-Loss` / `Take-Profit` tự động.

---

## 3. Cấu trúc Thư mục Dự án (Project Structure)

```text
btc-ai-quant-bot/
├── docs/                           # Bộ 6 tài liệu kiến trúc & luật AI
├── cache/
│   └── macro_sentiment.json        # Cache tin tức từ Hydrogen (cập nhật mỗi 2h)
├── config/
│   ├── settings.py                 # Cấu hình đòn bẩy, % rủi ro, ngưỡng Gatekeeper
│   └── .env                        # API Keys (Google AI Studio, Binance Testnet/Live)
├── data/
│   ├── fetcher.py                  # Kéo dữ liệu CCXT & nén Minified JSON
│   └── indicators.py               # Tính chỉ báo kỹ thuật bằng pandas-ta
├── ml_engine/
│   ├── train.py                    # Script huấn luyện LightGBM
│   └── predictor.py                # Dự đoán xác suất & chạy Gatekeeper
├── agents/
│   ├── schemas.py                  # Pydantic Schemas ép kiểu JSON Output
│   ├── news_worker.py              # Gọi Gemini 4 Hydrogen + Google Search
│   └── argon_debate.py             # Chạy luồng Phân tích & Phản biện trên Argon
├── execution/
│   ├── risk_guardrails.py          # Khóa an toàn vốn & tính Position Size
│   └── order_manager.py            # Đặt lệnh CCXT (Isolated + Atomic SL/TP)
├── logs/
│   └── audit_trades.jsonl          # Lưu log dữ liệu đầu vào/ra để audit hallucination
├── main.py                         # Vòng lặp điều phối chính (Event Loop)
└── requirements.txt                # Danh sách thư viện Python
```
