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

# Vercel에서 Flask 앱을 인식할 수 있도록 'app' 변수를 사용합니다.
app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['POST'])
def handler(path):
    # 1. 요청으로부터 JSON 데이터 받기
    data = request.get_json()
    image_url = data.get('imageUrl')
    question_text = data.get('questionText')

    if not image_url or not question_text:
        return jsonify({"error": "imageUrl and questionText are required."}), 400

    try:
        # 2. 이미지 다운로드
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        # 3. Gemini API에 보낼 프롬프트 구성
        prompt = f"""
        당신은 CAPTCHA 해결 전문가입니다.
        질문: "{question_text}"
        주어진 지도 이미지에서 질문의 패턴에 맞는 단어를 찾은 뒤, 빈칸에 들어갈 글자만 정확하게 응답하세요.
        다른 설명은 절대 추가하지 말고, 오직 정답 텍스트만 반환하세요.
        예를 들어, 질문이 '[빈칸]나은행'이고 이미지에 '하나은행'이 있다면 '하'라고만 대답해야 합니다.
        """

        # 4. Gemini API 호출
        api_response = model.generate_content([prompt, img])
        answer = api_response.text.strip()
        
        # 5. 정답을 JSON 형태로 반환
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# 로컬 테스트용이 아닌, Vercel 배포를 위한 핸들러입니다.
# 파일 이름이 solver.py 이므로, API 주소는 /api/solver 가 됩니다.
