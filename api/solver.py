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

        # --- 여기가 수정된 부분입니다 ---
        # 더 이상 사용되지 않는 'gemini-pro-vision' 대신, 최신 비전 모델 이름을 사용합니다.
        model = genai.GenerativeModel('gemini-1.5-flash-latest') 
        
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        prompt = f"당신은 CAPTCHA 해결 전문가입니다. 질문: \"{question_text}\". 주어진 이미지에서 질문의 패턴에 맞는 단어를 찾고, 빈칸에 들어갈 글자만 정확하게 응답하세요. 다른 설명은 절대 추가하지 마세요. 예를 들어, 질문이 '[빈칸]나은행'이고 이미지에 '하나은행'이 있다면 '하'라고만 대답해야 합니다."

        api_response = model.generate_content([prompt, img])
        answer = api_response.text.strip()
        
        return jsonify({"answer": answer}), 200, headers

    except Exception as e:
        print("--- ERROR ---")
        print(traceback.format_exc())
        print("-------------")
        return jsonify({"error": f"서버 내부 오류: {type(e).__name__} - {str(e)}"}), 500, headers
