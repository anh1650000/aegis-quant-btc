# 05_PROMPTS_AND_SCHEMAS.md — Bộ Prompt & Schema Tối Ưu Cho Google AI Pro

Tài liệu này định nghĩa cấu trúc dữ liệu **Pydantic Schemas** và **System Prompts** được tinh chỉnh đặc biệt cho gói **Google AI Pro**, sử dụng thư viện `google-genai` SDK mới nhất.

---

## 1. Cấu Hình Chung & Nguyên Tắc Tiết Kiệm Token

* **SDK Bắt buộc:** `from google import genai` (không dùng thư viện cũ `google-generativeai`).
* **Model Routing:**
  * `gemini-4-hydrogen`: Dùng kèm `GoogleSearch` tool để cào tin vĩ mô/crypto mỗi 2 giờ và lưu vào file cache.
  * `gemini-4-argon`: Dùng cho cả 2 vai trò **Lead Analyst** và **Devil's Advocate** (chỉ kích hoạt khi vượt qua Cổng gác Gatekeeper).
* **Prompt Caching:** Phần `system_instruction` được giữ cố định 100% giữa các lần gọi để tận dụng cơ chế Implicit/Explicit Context Caching của Google AI Studio.
* **Ép kiểu đầu ra:** Sử dụng `response_mime_type="application/json"` và `response_schema` kết hợp `max_output_tokens=450`.

---

## 2. Pydantic Schemas (`src/agents/schemas.py`)

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class MacroSentimentOutput(BaseModel):
    high_impact_event_within_4h: bool = Field(
        description="True nếu có tin vĩ mô đỏ (CPI, FOMC, Non-farm, SEC) trong 4h tới."
    )
    event_name: Optional[str] = Field(
        default=None, description="Tên sự kiện sắp diễn ra (nếu có), tối đa 50 ký tự."
    )
    market_bias: TradeDirection = Field(
        description="Xu hướng tin tức tổng thể trong 12h qua."
    )
    summary_bullets: List[str] = Field(
        max_length=3,
        description="Tối đa 3 gạch đầu dòng ngắn gọn (dưới 15 từ/ý) tóm tắt tin nóng BTC."
    )

class AnalystProposalOutput(BaseModel):
    decision: TradeDirection = Field(
        description="Chỉ chọn LONG hoặc SHORT nếu có sự hợp lưu rõ ràng. Ngược lại chọn NEUTRAL."
    )
    confidence_score: int = Field(
        ge=0, le=100, description="Điểm tự tin từ 0-100 dựa trên dữ liệu JSON."
    )
    entry_price: float = Field(description="Giá vào lệnh đề xuất (lấy theo giá thị trường hoặc vùng hỗ trợ/kháng cự gần nhất).")
    stop_loss: float = Field(description="Điểm cắt lỗ bắt buộc dựa trên cấu trúc giá hoặc ATR.")
    take_profit: float = Field(description="Điểm chốt lời mục tiêu đảm bảo R:R >= 1.8.")
    rationale: str = Field(
        max_length=200, description="Giải thích ngắn gọn lý do vào lệnh, trích dẫn đúng số liệu từ JSON."
    )

class RiskCritiqueOutput(BaseModel):
    approve_trade: bool = Field(
        description="False nếu phát hiện rủi ro quét thanh khoản, ngược xu hướng lớn hoặc Funding Rate bất lợi."
    )
    adjusted_confidence: int = Field(
        ge=0, le=100, description="Điểm tự tin sau khi trừ điểm rủi ro."
    )
    critical_flaws: List[str] = Field(
        max_length=3,
        description="Tối đa 3 điểm yếu chí mạng có thể khiến lệnh chạm Stop-Loss."
    )
```

---

## 3. System Prompts & Code Triển Khai (`src/agents/prompts.py`)

### A. Macro & News Sentinel (`gemini-4-hydrogen`)
*Chạy định kỳ 2 tiếng/lần via Cronjob, lưu output ra `data/news_cache.json`.*

```python
MACRO_SYSTEM_PROMPT = """
Bạn là Macro & Crypto News Sentinel. Nhiệm vụ của bạn là tìm kiếm tin tức thực tế về Bitcoin (BTC) và kinh tế vĩ mô Mỹ trong 12 giờ qua.
QUY TẮC BẮT BUỘC:
1. Chỉ trích xuất sự kiện có thật từ kết quả tìm kiếm. Tuyệt đối không suy đoán giá.
2. Kiểm tra lịch kinh tế (CPI, FOMC, Lãi suất Fed, Non-farm) trong 4 giờ tới. Nếu có, đặt high_impact_event_within_4h = True.
3. Viết cực kỳ ngắn gọn để tiết kiệm token.
"""
```

### B. Lead Technical Analyst (`gemini-4-argon` - Lượt 1)
*Nhận Minified JSON từ Tầng 1 + Tầng 2 + `news_cache.json`.*

```python
ANALYST_SYSTEM_PROMPT = """
Bạn là Lead Quantitative Analyst chuyên giao dịch BTC/USDT Perpetual Futures.
LUẬT BẤT DI BẤT DỊCH:
1. CHỈ sử dụng các con số có trong JSON đầu vào. Cấm tự tính toán chỉ báo hoặc bịa số liệu.
2. Nếu thị trường đi ngang (ADX < 20) hoặc không có sự đồng thuận giữa khung H1 và H4, bắt buộc trả về decision = NEUTRAL.
3. Điểm Stop-Loss phải đặt ngoài vùng nhiễu (tối thiểu 1.2x ATR_14). Điểm Take-Profit phải tạo tỷ lệ Risk:Reward >= 1.8.
4. Giải thích súc tích dưới 200 ký tự, nêu rõ chỉ số nào hỗ trợ quyết định.
"""
```

### C. Devil's Advocate / Risk Manager (`gemini-4-argon` - Lượt 2)
*Chỉ gọi khi Lượt 1 trả về `LONG` hoặc `SHORT`. Đóng vai người phản biện cực đoan.*

```python
CRITIC_SYSTEM_PROMPT = """
Bạn là Chief Risk Officer (CRO) có nhiệm vụ BÁC BỎ đề xuất giao dịch của Lead Analyst để bảo vệ vốn.
HÃY TÌM MỌI LÝ DO ĐỂ TỪ CHỐI LỆNH NÀY DỰA TRÊN JSON:
1. Kiểm tra Funding Rate: Nếu đề xuất LONG nhưng Funding Rate > 0.03% (quá dương), cảnh báo rủi ro Long Squeeze và đặt approve_trade = False. Ngược lại với SHORT nếu Funding < -0.03%.
2. Kiểm tra Open Interest (OI) và Volume: Giá tăng nhưng OI giảm hoặc Volume yếu là dấu hiệu bull-trap -> Từ chối.
3. Kiểm tra vị trí Stop-Loss: Nếu SL đặt quá sát các mốc số tròn (ví dụ: 90000, 95000) nơi dễ bị quét thanh khoản -> Từ chối.
Chỉ đặt approve_trade = True khi không tìm thấy lỗ hổng nghiêm trọng nào.
"""
```

---

## 4. Mẫu Hàm Gọi API Chuẩn Google AI Pro (`src/agents/runner.py`)

```python
import json
from google import genai
from google.genai import types
from src.agents.schemas import AnalystProposalOutput, RiskCritiqueOutput
from src.agents.prompts import ANALYST_SYSTEM_PROMPT, CRITIC_SYSTEM_PROMPT

client = genai.Client() # Tự động đọc biến môi trường GEMINI_API_KEY

def run_argon_debate(market_context: dict) -> dict:
    # Nén JSON tối đa để tiết kiệm input token
    minified_payload = json.dumps(market_context, separators=(',', ':'))
    
    # Lượt 1: Lead Analyst phân tích
    proposal_res = client.models.generate_content(
        model="gemini-4-argon",
        contents=f"Dữ liệu thị trường hiện tại: {minified_payload}",
        config=types.GenerateContentConfig(
            system_instruction=ANALYST_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=AnalystProposalOutput,
            temperature=0.1, # Giữ nhiệt độ thấp để bám sát số liệu
            max_output_tokens=400,
        ),
    )
    proposal = AnalystProposalOutput.model_validate_json(proposal_res.text)
    
    # Cổng chặn sớm: Nếu NEUTRAL thì dừng ngay, tiết kiệm 50% token lượt 2
    if proposal.decision == "NEUTRAL" or proposal.confidence_score < 70:
        return {"status": "SKIPPED", "proposal": proposal.model_dump()}

    # Lượt 2: Devil's Advocate phản biện
    critic_input = json.dumps({
        "market": market_context,
        "proposal": proposal.model_dump()
    }, separators=(',', ':'))

    critic_res = client.models.generate_content(
        model="gemini-4-argon",
        contents=f"Hãy phản biện đề xuất này: {critic_input}",
        config=types.GenerateContentConfig(
            system_instruction=CRITIC_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RiskCritiqueOutput,
            temperature=0.2,
            max_output_tokens=400,
        ),
    )
    critique = RiskCritiqueOutput.model_validate_json(critic_res.text)
    
    return {
        "status": "APPROVED" if critique.approve_trade else "REJECTED",
        "proposal": proposal.model_dump(),
        "critique": critique.model_dump()
    }
```