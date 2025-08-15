from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO
import traceback # 에러 상세 추적을 위해 추가

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
        # 1. API 키 확인
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=api_key)

        # 2. 요청 데이터 확인
        data = request.get_json()
        if not data or 'imageUrl' not in data or 'questionText' not in data:
            raise ValueError("imageUrl과 questionText가 요청에 포함되지 않았습니다.")
        
        image_url = data['imageUrl']
        question_text = data['questionText']

        # 3. 모델 생성 및 API 호출
        model = genai.GenerativeModel('gemini-pro-vision')
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        prompt = f"당신은 CAPTCHA 해결 전문가입니다. 질문: \"{question_text}\". 주어진 이미지에서 질문의 패턴에 맞는 단어를 찾고, 빈칸에 들어갈 글자만 정확하게 응답하세요. 다른 설명은 절대 추가하지 마세요. 예를 들어, 질문이 '[빈칸]나은행'이고 이미지에 '하나은행'이 있다면 '하'라고만 대답해야 합니다."

        api_response = model.generate_content([prompt, img])
        answer = api_response.text.strip()
        
        return jsonify({"answer": answer}), 200, headers

    except Exception as e:
        # 에러 발생 시, Vercel 로그에 상세 내용을 출력하고 클라이언트에게도 에러 메시지를 전달합니다.
        print("--- ERROR ---")
        print(traceback.format_exc()) # Vercel 로그에 전체 에러 스택 출력
        print("-------------")
        # 클라이언트에게는 간단한 에러 타입과 메시지를 전달
        return jsonify({"error": f"서버 내부 오류: {type(e).__name__} - {str(e)}"}), 500, headers
