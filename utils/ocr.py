import io
import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import re

# Gemini OCR Prompt
OCR_PROMPT = """
You are an expert at analyzing receipts from Vietnam, Korea, and English-speaking countries.
Extract the following from the receipt image:
1. Date (YYYY-MM-DD)
2. Time (HH:MM)
3. Store Name
4. Each line item: name, unit price (in VND), quantity
5. Payment Method: Cash or Card
6. Receipt total (the grand total printed on the receipt, in VND). Use 0 if not found.

If information is missing, use empty string or 0.
Return ONLY valid JSON in this exact format:
{
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "store_name": "Store Name",
  "items": [
    {"name": "품목명", "unit_price": 5300, "quantity": 1},
    {"name": "품목명2", "unit_price": 3500, "quantity": 2}
  ],
  "receipt_total": 12300,
  "payment_method": "Cash"
}
"""

def parse_receipt(image: Image) -> dict:
    """Gemini API를 사용하여 영수증 이미지를 분석하고 JSON 데이터를 반환합니다."""
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Gemini API Key가 secrets.toml에 설정되지 않았습니다.")
            return {}
        
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash')

        # PIL Image → bytes 변환 (SDK 버전 호환성)
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='JPEG')
        image_part = {"mime_type": "image/jpeg", "data": img_bytes.getvalue()}

        response = model.generate_content([OCR_PROMPT, image_part])
        
        # JSON 부분만 추출 (마크다운 코드 블록 등 제거)
        content = response.text
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if json_match:
            return json.loads(json_match.group())
        else:
            st.error("OCR 결과에서 JSON 형식을 찾을 수 없습니다.")
            return {}
            
    except Exception as e:
        st.error(f"OCR 처리 중 오류 발생: {type(e).__name__}: {e}")
        return {}
