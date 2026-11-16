# 03_PROJECT_ROADMAP - Lộ Trình Triển Khai Dự Án (6 Tuần)

## Tuần 1: Xây dựng Data Pipeline & Lớp Khóa An Toàn (Deterministic Core)
* **Mục tiêu:** Hoàn thiện hạ tầng lấy dữ liệu sàn và các hàm toán học chuẩn xác 100% (chưa dùng đến LLM).
* **Công việc chi tiết:**
  * Thiết lập môi trường Python 3.11+, cài đặt `ccxt`, `pandas-ta`, `pydantic`, `google-genai`.
  * Viết module `data/fetcher.py` kết nối Binance Futures Public API lấy nến `15m`, `1h`, `4h`, `Funding Rate` và `Open Interest`.
  * Viết module `data/indicators.py` tính chỉ báo kỹ thuật và hàm nén dữ liệu thành **Minified JSON** (`< 400 tokens`).
  * Viết module `execution/risk_guardrails.py` hiện thực hóa toàn bộ bảng khóa an toàn ở Phần B của file `02_AI_RULES_AND_GUARDRAILS.md` kèm Unit Test.

## Tuần 2: Huấn luyện Mô hình ML & Xây dựng Cổng Gác (Gatekeeper)
* **Mục tiêu:** Tạo bộ lọc định lượng để giảm 85% số lần gọi API LLM, bảo vệ quota Google AI Pro.
* **Công việc chi tiết:**
  * Tải dữ liệu lịch sử BTC/USDT khung `1h` và `15m` trong 3 năm gần nhất.
  * Xây dựng bộ đặc trưng (Feature Engineering): tỷ suất sinh lời logarit, độ biến động ATR chuẩn hóa, độ lệch chuẩn khối lượng, khoảng cách tới các đường EMA.
  * Train mô hình phân loại **LightGBM** dự đoán xác suất giá chạm mức chốt lời (`+1.5 * ATR`) trước khi chạm cắt lỗ (`-1.0 * ATR`).
  * Thiết lập ngưỡng lọc `Gatekeeper` trong `ml_engine/predictor.py` (chỉ mở cổng khi xác suất `>= 0.65`).

## Tuần 3: Tích hợp Google AI Pro (`Hydrogen` & `Argon`)
* **Mục tiêu:** Kết nối API Google AI Studio, cấu hình Structured Outputs và kiểm thử chống ảo giác số liệu.
* **Công việc chi tiết:**
  * Viết `agents/news_worker.py` sử dụng **`gemini-4-hydrogen`** tích hợp công cụ `Google Search` để quét tin vĩ mô/crypto mỗi 2 tiếng và ghi ra `cache/macro_sentiment.json`.
  * Viết `agents/argon_debate.py` sử dụng **`gemini-4-argon`** với `response_schema` (Pydantic) cho 2 vai trò: *Analyst* và *Devil's Advocate*.
  * Tối ưu `system_instruction` cố định để kích hoạt Prompt Caching, giảm chi phí và độ trễ.

## Tuần 4: Hợp nhất Luồng & Ghi Log Kiểm Toán (Audit & Observability)
* **Mục tiêu:** Chạy toàn bộ hệ thống khép kín ở chế độ **Dry-Run** (mô phỏng trên dữ liệu thật, không vào tiền).
* **Công việc chi tiết:**
  * Viết `main.py` điều phối vòng lặp sự kiện (Event Loop) chạy mỗi 15 phút.
  * Xây dựng hệ thống ghi log chi tiết vào `logs/audit_trades.jsonl` lưu lại toàn bộ: *JSON đầu vào -> Dự đoán ML -> Output của Argon Analyst -> Phản biện của Argon Risk Manager -> Quyết định của Guardrails*.
  * Kiểm tra thủ công 50 phiên chạy để đảm bảo 0% lỗi bịa số liệu (Hallucination).

## Tuần 5: Chạy Thử Nghiệm trên Binance Futures Testnet
* **Mục tiêu:** Kiểm tra khả năng khớp lệnh thực tế, độ trễ mạng và xử lý lỗi API sàn.
* **Công việc chi tiết:**
  * Viết `execution/order_manager.py` đặt lệnh `LIMIT` / `MARKET` kèm `STOP_MARKET` và `TAKE_PROFIT_MARKET` trên Binance Testnet.
  * Tích hợp thông báo đẩy qua **Telegram Bot** mỗi khi hệ thống mở lệnh, đóng lệnh hoặc từ chối kèo.
  * Theo dõi liên tục trong 7 ngày để đánh giá tỷ lệ thắng (Winrate), mức sụt giảm vốn (Max Drawdown) và lượng quota Google AI Pro tiêu thụ thực tế.

## Tuần 6: Tinh chỉnh Tham số & Triển khai Thực tế (Vốn Nhỏ)
* **Mục tiêu:** Tối ưu hóa chiến lược và đưa vào vận hành thực tế an toàn.
* **Công việc chi tiết:**
  * Tinh chỉnh lại ngưỡng lọc của `Gatekeeper` và các tham số ATR dựa trên kết quả tuần 5.
  * Đóng gói hệ thống bằng **Docker** và triển khai lên VPS (đặt máy chủ ở khu vực Tokyo/Singapore để tối ưu độ trễ tới máy chủ sàn).
  * Chạy Live với số vốn thử nghiệm nhỏ (ví dụ: 100 - 200 USDT) và bật IP Whitelist cho API Key sàn.
