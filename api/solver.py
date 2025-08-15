# api/solver.py (수정된 버전)
from http.server import BaseHTTPRequestHandler
import json
import os
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO

# Vercel 환경 변수에서 API 키를 안전하게 불러옵니다.
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro-vision')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. 요청으로부터 JSON 데이터 읽기
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        image_url = data.get('imageUrl')
        question_text = data.get('questionText')

        if not image_url or not question_text:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "imageUrl and questionText are required."}).encode())
            return

        try:
            # 2. 이미지 다운로드
            response = requests.get(image_url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))

            # 3. Gemini API 프롬프트 구성
            prompt = f"""
            당신은 CAPTCHA 해결 전문가입니다. 질문: "{question_text}". 주어진 이미지에서 질문의 패턴에 맞는 단어를 찾고, 빈칸에 들어갈 글자만 정확하게 응답하세요. 다른 설명은 절대 추가하지 마세요. 예를 들어, 질문이 '[빈칸]나은행'이고 이미지에 '하나은행'이 있다면 '하'라고만 대답해야 합니다.
            """

            # 4. Gemini API 호출
            api_response = model.generate_content([prompt, img])
            answer = api_response.text.strip()
            
            # 5. 성공 응답 전송
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"answer": answer}).encode())

        except Exception as e:
            # 5. 에러 응답 전송
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"An error occurred: {str(e)}"}).encode())
