from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO
import traceback

app = Flask(__name__)

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

        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        # --- 여기가 수정된 부분입니다: 새로운 문제 유형을 AI에게 가르칩니다 ---
        prompt = f"""
        당신은 두 가지 유형의 시각적 CAPTCHA를 해결하는 초정밀 AI 전문가입니다.

        **[임무]**
        주어진 질문의 유형을 먼저 파악한 뒤, 그에 맞는 작업 절차에 따라 문제를 해결하세요.

        ---
        **[유형 1: 빈칸 채우기]**
        *   **질문 형태:** "광진 빈칸 라", "빈칸 원빌딩" 등 '빈칸' 이라는 단어가 포함됨.
        *   **작업 절차:**
            1. '빈칸'을 기준으로 **앞부분(prefix)**과 **뒷부분(suffix)**을 분리합니다.
            2. 이미지에서 `prefix`로 시작하고 `suffix`로 끝나는 **완전한 단어**를 찾습니다.
            3. 찾아낸 단어에서 `prefix`와 `suffix`를 제거하여 '빈칸'에 들어갈 부분만 추출합니다.

        **[유형 2: 전체 명칭 찾기]**
        *   **질문 형태:** "아파트의 전체 명칭을 입력해주세요", "학교의 전체 명칭을..." 등 특정 대상의 '전체 명칭'을 요구함.
        *   **작업 절차:**
            1. 질문에서 요구하는 대상(예: 아파트, 학교, 약국)이 무엇인지 파악합니다.
            2. 이미지에서 해당 대상 중 가장 눈에 띄거나 명확한 것의 **정확한 전체 이름**을 읽어냅니다.
            3. 읽어낸 전체 이름을 그대로 추출합니다.

        **[출력 규칙]**
        *   어떤 유형의 문제든, 최종적으로 추출한 정답 텍스트만 출력해야 합니다.
        *   다른 어떤 설명, 따옴표, 기호도 절대 포함하지 마세요.

        ---
        **[실제 문제 해결]**
        위의 지침을 완벽하게 따라서 아래 문제를 해결하세요.
        **질문:** "{question_text}"
        """

        api_response = model.generate_content([prompt, img])
        answer = api_response.text.strip()
        
        return jsonify({"answer": answer}), 200, headers

    except Exception as e:
        print("--- ERROR ---"); print(traceback.format_exc()); print("-------------")
        return jsonify({"error": f"서버 내부 오류: {type(e).__name__} - {str(e)}"}), 500, headers
