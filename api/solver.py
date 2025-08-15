from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO
import traceback

app = Flask(__name__)

# --- 여기가 수정된 부분입니다: Google AI의 안전 필터 설정을 정의합니다 ---
# 모든 카테고리에 대해 필터링을 비활성화(NONE)하여 AI가 답변을 거부하지 않도록 합니다.
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

@app.route('/api/solver', methods=['POST', 'OPTIONS'])
def solve_captcha():
    if request.method == 'OPTIONS':
        headers = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' }
        return ('', 204, headers)

    headers = { 'Access-Control-Allow-Origin': '*' }
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key: raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=api_key)

        data = request.get_json()
        if not data or 'imageUrl' not in data or 'questionText' not in data: raise ValueError("imageUrl과 questionText가 요청에 포함되지 않았습니다.")
        
        image_url = data['imageUrl']
        question_text = data['questionText']

        # 모델을 생성할 때 안전 설정을 함께 전달합니다.
        model = genai.GenerativeModel('gemini-1.5-pro-latest', safety_settings=safety_settings)
        
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        prompt = f"""
        당신은 두 가지 유형의 시각적 CAPTCHA를 해결하는 초정밀 AI 전문가입니다.
        **[임무]** 주어진 질문의 유형을 먼저 파악한 뒤, 그에 맞는 작업 절차에 따라 문제를 해결하세요.
        ---
        **[유형 1: 빈칸 채우기]**
        *   **질문 형태:** "광진 빈칸 라", "빈칸 원빌딩" 등 '빈칸' 이라는 단어가 포함됨.
        *   **작업 절차:** '빈칸'을 기준으로 앞/뒤 부분을 분리하고, 이미지에서 완전한 단어를 찾아 빈칸 부분을 추출합니다.
        **[유형 2: 전체 명칭 찾기]**
        *   **질문 형태:** "아파트의 전체 명칭을 입력해주세요", "학교의 전체 명칭을..." 등 특정 대상의 '전체 명칭'을 요구함.
        *   **작업 절차:** 질문에서 요구하는 대상(예: 아파트, 학교)의 정확한 전체 이름을 이미지에서 읽어냅니다.
        ---
        **[출력 규칙]** 어떤 유형이든, 최종 정답 텍스트만 출력해야 합니다. 다른 설명은 절대 포함하지 마세요.
        ---
        **[실제 문제 해결]**
        **질문:** "{question_text}"
        """

        # API를 호출할 때도 안전 설정을 전달할 수 있습니다. (모델 생성 시 전달했으므로 이중 안전장치)
        api_response = model.generate_content([prompt, img], safety_settings=safety_settings)
        
        # AI가 안전 문제 등으로 답변을 비웠을 경우를 대비한 추가 방어 코드
        if not api_response.parts:
            raise ValueError("AI가 안전 필터 또는 기타 이유로 답변 생성을 거부했습니다.")

        answer = api_response.text.strip()
        
        return jsonify({"answer": answer}), 200, headers

    except Exception as e:
        print("--- ERROR ---"); print(traceback.format_exc()); print("-------------")
        return jsonify({"error": f"서버 내부 오류: {type(e).__name__} - {str(e)}"}), 500, headers
