from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO
import traceback

# Flask 애플리케이션 초기화
app = Flask(__name__)

# Google AI의 안전 필터 설정 (모든 카테고리 비활성화)
# AI가 안전 문제로 답변을 거부하는 것을 방지합니다.
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

@app.route('/api/solver', methods=['POST', 'OPTIONS'])
def solve_captcha():
    # 브라우저가 보내는 CORS Preflight 요청(OPTIONS)에 대한 응답 처리
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-control-allow-headers': 'Content-Type',
        }
        return ('', 204, headers)

    # 모든 실제 응답에 CORS 헤더를 포함하여 브라우저의 접근을 허용
    headers = { 'Access-Control-Allow-Origin': '*' }
    
    try:
        # 1. 환경 변수에서 Google API 키를 안전하게 불러옵니다.
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=api_key)

        # 2. 확장 프로그램이 보낸 JSON 데이터를 수신합니다.
        data = request.get_json()
        if not data or 'imageUrl' not in data or 'questionText' not in data:
            raise ValueError("imageUrl과 questionText가 요청에 포함되지 않았습니다.")
        
        image_url = data['imageUrl']
        question_text = data['questionText']
        
        # 3. 확장 프로그램 UI에서 사용자가 선택한 모델 이름을 받아옵니다.
        # 만약 정보가 없다면, 'gemini-1.5-flash-latest'를 기본값으로 사용합니다.
        model_name = data.get('model', 'gemini-1.5-flash-latest')

        # 4. 전달받은 모델 이름과 안전 설정으로 AI 모델을 생성합니다.
        model = genai.GenerativeModel(model_name, safety_settings=safety_settings)
        
        # 5. 이미지 URL에서 이미지를 다운로드하고 처리합니다.
        response = requests.get(image_url)
        response.raise_for_status() # HTTP 에러가 있으면 예외 발생
        img = Image.open(BytesIO(response.content))

        # 6. 두 가지 문제 유형과 모든 예외 케이스를 처리하는 최종 프롬프트를 구성합니다.
        prompt = f"""
        당신은 시각적 CAPTCHA를 해결하는 초정밀 AI 전문가입니다. 당신의 임무는 '빈칸' 문제의 정답률을 100%로 만드는 것입니다.

        **[핵심 원칙]**
        1.  **'빈칸'은 글자 수나 위치가 정해져 있지 않다:** '빈칸'은 단어의 시작, 중간, 끝 어디에나 올 수 있으며, 한 글자 이상일 수 있다.
        2.  **문자열 치환으로 접근하라:** `질문 패턴`에서 '빈칸'을 `정답`으로 바꾸면 `이미지 속 전체 단어`가 되어야 한다는 공식을 따른다.
        3.  **빈칸에는 단어가 아닌 글자가 들어간다:** 단어에 집착하면 틀린다. '천S', '5', 'A', '말좋', '파트' 와 같이 단어가 아닌 것들이 들어간다.

        **[엄격한 작업 절차]**
        1.  **질문 분석:** 질문 텍스트(`{question_text}`)에서 '빈칸'을 기준으로 **앞부분(prefix)**과 **뒷부분(suffix)**을 정확히 분리합니다. 둘 중 하나는 비어있을 수 있습니다.
        2.  **이미지 OCR:** 이미지 안의 모든 텍스트를 정밀하게 읽어냅니다.
        3.  **완전한 단어 탐색:** OCR 결과 중에서 `prefix`로 시작하고 `suffix`로 끝나는 가장 그럴듯한 **완전한 단어**를 찾습니다.
        4.  **정답 추출:** 3단계에서 찾은 완전한 단어에서 `prefix`와 `suffix`를 제거하여 '빈칸'에 들어갈 부분만 남깁니다. 이것이 최종 정답입니다.
        5.  **최종 출력:** 4단계에서 추출한 정답 텍스트만 출력합니다. 다른 어떤 설명이나 기호도 절대 포함하지 마세요.

        **[사고 과정 훈련 예시]**
        *   **예시 1 (중간 빈칸):** 질문: "참 빈칸 병원" -> 이미지 단어: '참좋은병원' -> 추론: '참좋은병원' - '참' - '병원' = '좋은' -> 정답: 좋은
        *   **예시 2 (시작 빈칸):** 질문: "빈칸 원빌딩" -> 이미지 단어: '청원빌딩' -> 추론: '청원빌딩' - '원빌딩' = '청' -> 정답: 청
        *   **예시 3 (끝 빈칸):** 질문: "참좋은병 빈칸" -> 이미지 단어: '참좋은병원' -> 추론: '참좋은병원' - '참좋은병' = '원' -> 정답: 원

        ---
        **[실제 문제 해결]**
        위의 핵심 원칙과 작업 절차를 완벽하게 따라서 아래 문제를 해결하세요.
        **질문:** "{question_text}"
        """

        # 7. 구성된 프롬프트와 이미지로 AI에게 답변을 요청합니다.
        api_response = model.generate_content([prompt, img], safety_settings=safety_settings)
        
        if not api_response.parts:
            raise ValueError("AI가 안전 필터 또는 기타 이유로 답변 생성을 거부했습니다.")

        answer = api_response.text.strip()
        
        # 8. 성공적으로 받은 정답을 클라이언트에게 반환합니다.
        return jsonify({"answer": answer}), 200, headers

    except Exception as e:
        # 에러 발생 시, Vercel 로그에 상세 내용을 출력하고 클라이언트에게도 에러 메시지를 전달합니다.
        print("--- ERROR ---"); 
        print(traceback.format_exc()) # Vercel 로그에 전체 에러 스택 출력
        print("-------------")
        # 클라이언트에게는 간단한 에러 타입과 메시지를 전달
        return jsonify({"error": f"서버 내부 오류: {type(e).__name__} - {str(e)}"}), 500, headers
