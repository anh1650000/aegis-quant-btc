# 00_SESSION_BOOTSTRAP - Khởi tạo Ngữ cảnh Dự án (Google AI Pro Edition)

## 1. Hướng dẫn sử dụng File này
Mỗi khi mở một cuộc hội thoại mới với AI Assistant (Cursor, Claude, Gemini) để tiếp tục phát triển dự án, hãy đính kèm file này đầu tiên kèm theo câu lệnh:
> *"Hãy đọc file `00_SESSION_BOOTSTRAP.md` và các tài liệu trong thư mục `docs/` để nắm rõ kiến trúc hệ thống, tối ưu quota gói Google AI Pro và tiếp tục triển khai từ điểm dừng hiện tại."*

---

## 2. Tóm tắt Dự án (Project Context)
* **Tên dự án:** Hybrid AI Trading System (BTC/USDT Perpetual Futures).
* **Tác giả:** Sinh viên năm cuối CS - Chuyên ngành AI Engineer.
* **Tài nguyên tính toán & Quota:** Đã sở hữu gói **Google AI Pro** (Truy cập đầy đủ **Gemini 4 Argon** và **Gemini 4 Hydrogen** qua Google AI Studio / Vertex AI với hạn mức cao, không sử dụng Gemini 4 Carbon để tránh lãng phí/vượt gói).
* **Triết lý thiết kế cốt lõi:** 
  1. *Deterministic Code (Python/ML)* làm toán, lọc nhiễu và kiểm soát rủi ro.
  2. *LLM (Gemini 4 Argon & Hydrogen)* chỉ làm nhiệm vụ tổng hợp tin tức, đối chiếu ngữ cảnh và phản biện rủi ro.
  3. *Event-Driven & Token Optimization:* Chỉ kích hoạt LLM khi có tín hiệu hợp lưu từ lớp ML/Kỹ thuật; ép đầu ra JSON ngắn gọn.

---

## 3. Bản đồ Tài liệu Dự án (Documentation Map)
1. `01_ARCHITECTURE_AND_SPEC.md`: Kiến trúc 4 tầng tối ưu cho cặp model `Hydrogen` + `Argon`, cơ chế Gatekeeper và cấu trúc thư mục.
2. `02_AI_RULES_AND_GUARDRAILS.md`: Bộ luật chống Hallucination và các ngưỡng khóa an toàn vốn bằng code thuần.
3. `03_PROJECT_ROADMAP.md`: Lộ trình triển khai chi tiết trong 6 tuần.
4. `04_PROGRESS_TRACKER.md`: Bảng theo dõi tiến độ, Audit Log chống ảo giác và KPIs kiểm thử.
5. `05_PROMPTS_AND_SCHEMAS.md`: Pydantic Schemas ép kiểu JSON và System Prompts đã tối ưu token cho `Gemini 4 Hydrogen` và `Gemini 4 Argon`.

---

## 4. Quy tắc làm việc cho AI Coding Assistant
* **Ưu tiên độ chính xác toán học:** Tuyệt đối không viết prompt bắt LLM tự tính chỉ báo kỹ thuật (RSI, EMA, ATR), khối lượng lệnh (Position Size), hay giá thanh lý (Liquidation Price). Mọi phép toán phải viết bằng hàm Python (`numpy`, `pandas-ta`).
* **Tối ưu Quota Google AI Pro:** Mọi luồng gọi API đều phải đi qua lớp `Gatekeeper` (lọc tín hiệu bằng code) và sử dụng `Minified JSON` cho dữ liệu đầu vào.
* **An toàn tài khoản:** Luôn cấu hình mặc định chế độ `Isolated Margin`, đặt lệnh kèm `Stop-Loss` và hỗ trợ chạy `Testnet / Dry-run` trước khi dùng API key thật.
