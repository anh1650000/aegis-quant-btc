# 02_AI_RULES_AND_GUARDRAILS - Bộ Luật AI & Khóa An Toàn Vốn

## Phần A: Bộ Luật Chống Hallucination & Tối Ưu Quota cho LLM

### Điều 1: Nguyên tắc Không Làm Toán (Zero-Math for LLM)
* **Quy định:** Tuyệt đối cấm `Gemini 4 Argon` và `Gemini 4 Hydrogen` tự tính toán các chỉ số kỹ thuật, tỷ lệ phần trăm biến động, khối lượng vào lệnh (Position Size), hay giá thanh lý (Liquidation Price).
* **Thực thi:** Mọi phép toán phải được thực hiện trước bằng thư viện `numpy` / `pandas` trong Python. LLM chỉ nhận các con số đã tính sẵn trong `Minified JSON`.

### Điều 2: Nguyên tắc Ngữ cảnh Khép kín (Grounded Context Only)
* **Quy định:** Khi phân tích kỹ thuật, `Gemini 4 Argon` chỉ được phép lập luận dựa trên các trường dữ liệu có mặt trong JSON đầu vào. Cấm tự suy diễn các mô hình giá hoặc mức hỗ trợ/kháng cự không tồn tại trong dữ liệu.
* **Thực thi:** Mọi giải thích của AI phải trích dẫn chính xác tên biến và giá trị số từ JSON (ví dụ: *"Do `rsi_1h=74.2` và `funding_rate=0.035%`"*). Nếu thiếu dữ liệu, AI bắt buộc trả về trạng thái `HOLD`.

### Điều 3: Nguyên tắc Tiết kiệm Token & Chống Lặp (Quota & Latency Protection)
* **Quy định:** Không gọi API LLM khi thị trường không có biến động đạt chuẩn. Giữ `system_instruction` cố định ở đầu mỗi request để tận dụng cơ chế **Prompt Caching** của Google AI Studio.
* **Thực thi:**
  * Dữ liệu JSON truyền vào prompt phải loại bỏ toàn bộ khoảng trắng thừa (`separators=(',', ':')`).
  * Ép tham số `max_output_tokens <= 450` cho mỗi lượt gọi Argon và `<= 300` cho Hydrogen.
  * Sử dụng `temperature = 0.1` cho Analyst và `temperature = 0.2` cho Devil's Advocate để đảm bảo tính nhất quán cao nhất.

### Điều 4: Nguyên tắc Phủ quyết Mặc định (Default-to-Hold)
* **Quy định:** Trong giao dịch Futures, đứng ngoài thị trường là một vị thế an toàn. Nếu có sự mâu thuẫn giữa tín hiệu kỹ thuật (`Argon Analyst`), cảnh báo phản biện (`Argon Risk Manager`), và tin tức vĩ mô (`Hydrogen Cache`), quyết định cuối cùng bắt buộc là `HOLD`.

---

## Phần B: Lớp Khóa An Toàn Cứng bằng Code (Hard-Coded Risk Guardrails)

Bất kể `Gemini 4 Argon` tự tin đến mức nào (`confidence_score = 99`), lệnh giao dịch sẽ bị code Python trong file `execution/risk_guardrails.py` **tự động hủy bỏ** nếu vi phạm bất kỳ ngưỡng nào sau đây:

| Thông số Rủi ro | Ngưỡng Bắt Buộc | Cơ chế Xử lý của Code Python |
| :--- | :--- | :--- |
| **Rủi ro tối đa / Lệnh** | `<= 1.5%` tổng vốn Futures | Tự động tính `Position Size = (Balance * 0.015) / |Entry - StopLoss|`. Không cho phép vào vượt khối lượng này. |
| **Tỷ lệ Rủi ro / Lợi nhuận (R:R)** | `>= 1.8` | Tính `R:R = |TakeProfit - Entry| / |Entry - StopLoss|`. Nếu `< 1.8`, tự động hủy lệnh (`REJECT`). |
| **Khoảng cách Stop-Loss** | `0.5 * ATR(14) <= SL <= 2.5 * ATR(14)` | Chặn các lệnh đặt SL quá sát (dễ bị quét nhiễu) hoặc quá xa (rủi ro biến động lớn). |
| **Chế độ Ký quỹ & Đòn bẩy** | `Isolated Margin`, Đòn bẩy `<= 10x` | Ép buộc gọi API đổi sang chế độ `ISOLATED` trước khi mở lệnh. Đảm bảo giá thanh lý nằm xa hơn giá Stop-Loss ít nhất 30%. |
| **Ngắt mạch Tin tức Đỏ** | `HIGH_IMPACT_EVENT == True` | Đọc file `cache/macro_sentiment.json`. Nếu sắp có tin CPI, FOMC, Non-farm trong vòng 2 giờ tới, khóa toàn bộ lệnh mới. |
| **Ngắt mạch Lỗ Ngày (Daily Drawdown)** | `<= 4.5%` tổng vốn / 24h | Nếu tài khoản lỗ chạm mức 4.5% trong ngày (tương đương 3 lệnh thua liên tiếp), hệ thống tự động ngủ đông 24 giờ. |
| **Giới hạn Vị thế Đồng thời** | Tối đa `1` vị thế mở | Không nhồi lệnh (DCA ngược xu hướng), không mở cùng lúc nhiều vị thế trên cặp BTC/USDT. |
