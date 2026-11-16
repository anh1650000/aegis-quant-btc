# 04_PROGRESS_TRACKER - Theo Dõi Tiến Độ & Kiểm Thử Chất Lượng

## 1. Bảng Tiến Độ Triển Khai (Task Checklist)

| Giai đoạn | Hạng mục công việc | File liên quan | Trạng thái | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **Tuần 1** | Khởi tạo cấu trúc thư mục & cài thư viện | `requirements.txt` | `[x] Hoàn thành` | Python 3.11+, `google-genai`, `ccxt` |
| **Tuần 1** | Kéo dữ liệu CCXT & nén Minified JSON | `src/data/fetcher.py` | `[x] Hoàn thành` | Public async fetcher và JSON không khoảng trắng |
| **Tuần 1** | Tính chỉ báo kỹ thuật bằng `pandas-ta` | `src/data/indicators.py` | `[x] Hoàn thành` | RSI, Bollinger Bands, Volume Ratio deterministic |
| **Tuần 1** | Viết hàm khóa an toàn & tính Position Size | `src/risk/guardrails.py` | `[x] Hoàn thành` | Unit tests cho R:R, liquidation, position size |
| **Tuần 2** | Tải dữ liệu lịch sử & Feature Engineering | `src/ml/train.py` | `[x] Hoàn thành` | Binance public history và feature builder |
| **Tuần 2** | Huấn luyện LightGBM & Cổng gác Gatekeeper | `src/ml/predictor.py`, `src/ml/gatekeeper.py` | `[x] Hoàn thành` | Ngưỡng mở cổng `Prob > 0.65` |
| **Tuần 3** | Tích hợp `Gemini 4 Hydrogen` cào tin cache | `src/agents/macro_sentinel.py` | `[x] Hoàn thành` | TTL 2 giờ, Google Search, Pydantic JSON |
| **Tuần 3** | Tích hợp `Gemini 4 Argon` (Analyst + Critic) | `src/agents/debate_graph.py` | `[x] Hoàn thành` | LangGraph, structured output, early exit |
| **Tuần 4** | Chạy Dry-run & Audit Log chống ảo giác | `src/main.py`, `src/execution/paper.py` | `[x] Hoàn thành` | Pipeline paper-mode và không gửi lệnh thật |
| **Tuần 5** | Kết nối Binance Testnet & Zalo OA Alert | `src/execution/order_manager.py`, `src/notifications/zalo_oa.py` | `[x] Hoàn thành` | DRY_RUN/TESTNET, Isolated, Atomic SL/TP, OAuth refresh và admin alert |
| **Tuần 5** | Audit log & KPI evaluation | `src/utils/audit_logger.py`, `scripts/evaluate_kpi.py` | `[x] Hoàn thành` | Giới hạn 50 phiên, Winrate, Max Drawdown, Hallucination, Token Savings |
| **Tuần 5** | Docker backend & worker | `Dockerfile`, `docker-compose.yml`, `.env.example` | `[x] Hoàn thành` | Backend FastAPI và worker dùng chung volume audit/token |

---

## 2. Nhật ký Kiểm thử Chống Hallucination (Audit Log)
*Ghi chép lại các trường hợp AI suy luận sai hoặc bịa số liệu trong quá trình chạy Dry-run để tinh chỉnh lại System Prompt.*

| Ngày | Phiên bản Prompt | Số mẫu kiểm tra | Số lỗi Hallucination | Mô tả lỗi (nếu có) & Cách khắc phục |
| :--- | :--- | :--- | :--- | :--- |
| *DD/MM/YYYY* | `v1.0` | `0` | `0` | *Ví dụ: Argon tự đoán vùng kháng cự cũ -> Đã thêm luật cấm đoán ngoài JSON.* |

---

## 3. Bộ Chỉ Số KPIs Bắt Buộc Trước Khi Dùng Tiền Thật (Go-Live Criteria)
Hệ thống chỉ được phép chuyển từ **Testnet** sang **Live API Key** khi đạt đủ toàn bộ 5 tiêu chí dưới đây trong ít nhất **14 ngày chạy liên tục**:

* [ ] **Tỷ lệ Hallucination:** `0%` (Mọi con số trích dẫn trong log của `Gemini 4 Argon` phải khớp chính xác với `Minified JSON` đầu vào).
* [ ] **Hiệu suất Quota Google AI Pro:** Trung bình `<= 10 lần gọi Argon/ngày` và `<= 12 lần gọi Hydrogen/ngày`, không gặp lỗi `429 Too Many Requests`.
* [ ] **An toàn Khớp lệnh:** `100%` lệnh mở trên Testnet đều ở chế độ `Isolated Margin` và có sẵn lệnh `Stop-Loss` đi kèm ngay lập tức.
* [ ] **Chỉ số Lợi nhuận Kỳ vọng (Profit Factor):** `>= 1.35` (Tổng lợi nhuận các lệnh thắng chia cho tổng thua lỗ các lệnh thua).
* [ ] **Mức Sụt Giảm Vốn Tối Đa (Max Drawdown):** `< 8%` trên tổng tài khoản Testnet.
