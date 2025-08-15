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
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)

    headers = { 'Access-Control-Allow-Origin': '*' }
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=api_key)

        data = request.get_json()
        if not data or 'imageUrl' not in data or 'questionText' not in data:
            raise ValueError("imageUrl과 questionText가 요청에 포함되지 않았습니다.")
        
        image_url = data['imageUrl']
        question_text = data['questionText']

        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        # --- 여기가 수정된 부분입니다: AI를 더 똑똑하게 만드는 새로운 프롬프트 ---
        prompt = f"""
        당신은 OCR과 추론을 사용하는 CAPTCHA 해결 전문가입니다.
        주어진 질문과 지도 이미지를 보고, '빈칸'에 들어갈 글자만 정확하게 찾아내세요.

        **작업 규칙:**
        1. 질문 텍스트에서 '빈칸'의 위치와 앞뒤 글자를 파악합니다. ('문제'와 같은 불필요한 단어는 무시하세요.)
        2. 지도 이미지에서 질문의 패턴과 일치하는 전체 단어를 찾습니다. (예: '광진', '라'가 보이면 '광진빌라'를 찾습니다.)
        3. 찾아낸 전체 단어에서 질문에 주어진 부분을 제외하여 '빈칸'에 들어갈 글자를 알아냅니다.
        4. 오직 '빈칸'에 들어갈 글자만 응답해야 합니다. 다른 설명, 따옴표, 줄바꿈은 절대 포함하지 마세요.
        5. 이미지는 반드시 지도에서 찾아낸 이미지이므로 지도에 들어갈 일반적인 단어의 일부가 빈칸으로 지정됩니다.

        **다양한 질문 유형 예시:**
        - 질문이 "광진 빈칸라" 이고 이미지에 "광진빌라"가 있다면, 정답은 "빌" 입니다.
        - 질문이 "빈칸 원빌딩" 이고 이미지에 "청원빌딩"이 있다면, 정답은 "청" 입니다.
        - 질문이 "이화산업빈칸" 이고 이미지에 "이화산업빌딩"이 있다면, 정답은 "빌딩" 입니다.
        - 질문이 "빈칸 나은행" 이고 이미지에 "하나은행"이 있다면, 정답은 "하" 입니다.
        - 질문이 "빈칸 K스카이뷰" 이고 이미지에 "인천SK스카이뷰"가 있다면, 정답은 "인천S" 입니다.
        - 질문이 "엔에스파크아빈칸" 이고 이미지에 "엔에스파크아파트"가 있다면, 정답은 "파트" 입니다.
        - 질문이 "대빈칸 케미칼" 이고 이미지에 "대원케미칼"이 있다면, 정답은 "원"입니다.

        **--- 현재 문제 ---**
        질문: "{question_text}"
        """

        api_response = model.generate_content([prompt, img])
        answer = api_response.text.strip()
        
        return jsonify({"answer": answer}), 200, headers

    except Exception as e:
        print("--- ERROR ---")
        print(traceback.format_exc())
        print("-------------")
        return jsonify({"error": f"서버 내부 오류: {type(e).__name__} - {str(e)}"}), 500, headers
