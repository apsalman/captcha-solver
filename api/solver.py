from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO

# Vercel 환경 변수에서 API 키를 안전하게 불러옵니다.
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro-vision')

app = Flask(__name__)

# /api/solver 주소로 POST와 OPTIONS 요청을 모두 허용합니다.
@app.route('/api/solver', methods=['POST', 'OPTIONS'])
def solve_captcha():
    # --- CORS Preflight 요청 처리 ---
    # 브라우저는 POST 요청을 보내기 전에 OPTIONS 메소드로 "보내도 괜찮아?" 라고 먼저 물어봅니다.
    # 이 요청에 대해 허가 헤더를 담아 응답해줘야 합니다.
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*', # 모든 도메인에서의 요청을 허용
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)

    # --- 기존 POST 요청 처리 ---
    # CORS 헤더를 추가하기 위해 모든 응답을 'response' 변수에 담아 처리합니다.
    headers = {
        'Access-Control-Allow-Origin': '*' # 실제 POST 요청 응답에도 허가 헤더를 포함해야 합니다.
    }
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400, headers
        
    image_url = data.get('imageUrl')
    question_text = data.get('questionText')

    if not image_url or not question_text:
        return jsonify({"error": "imageUrl and questionText are required."}), 400, headers

    try:
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        prompt = f"""
        당신은 CAPTCHA 해결 전문가입니다.
        질문: "{question_text}"
        주어진 지도 이미지에서 질문의 패턴에 맞는 단어를 찾은 뒤, 빈칸에 들어갈 글자만 정확하게 응답하세요.
        다른 설명은 절대 추가하지 말고, 오직 정답 텍스트만 반환하세요.
        예를 들어, 질문이 '[빈칸]나은행'이고 이미지에 '하나은행'이 있다면 '하'라고만 대답해야 합니다.
        """

        api_response = model.generate_content([prompt, img])
        answer = api_response.text.strip()
        
        return jsonify({"answer": answer}), 200, headers

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500, headers
