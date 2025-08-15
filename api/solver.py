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
        model = genai.GenerativeModel('gemini-2.0-flash-lite', safety_settings=safety_settings)
        
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        prompt = f"""
        당신은 시각적 CAPTCHA를 해결하는 초정밀 AI 전문가입니다. 당신의 임무는 '빈칸' 문제의 정답률을 100%로 만드는 것입니다.

        **[핵심 원칙]**
        1.  **'빈칸'은 글자 수나 위치가 정해져 있지 않다:** '빈칸'은 단어의 시작, 중간, 끝 어디에나 올 수 있으며, 한 글자 이상일 수 있다.
        2.  **문자열 치환으로 접근하라:** `질문 패턴`에서 '빈칸'을 `정답`으로 바꾸면 `이미지 속 전체 단어`가 되어야 한다는 공식을 따른다.

        **[엄격한 작업 절차]**
        1.  **질문 분석:** 질문 텍스트(`{question_text}`)에서 '빈칸'을 기준으로 **앞부분(prefix)**과 **뒷부분(suffix)**을 정확히 분리합니다. 둘 중 하나는 비어있을 수 있습니다.
        2.  **이미지 OCR:** 이미지 안의 모든 텍스트를 정밀하게 읽어냅니다.
        3.  **완전한 단어 탐색:** OCR 결과 중에서 `prefix`로 시작하고 `suffix`로 끝나는 가장 그럴듯한 **완전한 단어**를 찾습니다.
        4.  **정답 추출:** 3단계에서 찾은 완전한 단어에서 `prefix`와 `suffix`를 제거하여 '빈칸'에 들어갈 부분만 남깁니다. 이것이 최종 정답입니다.
        5.  **최종 출력:** 4단계에서 추출한 정답 텍스트만 출력합니다. 다른 어떤 설명이나 기호도 절대 포함하지 마세요.

        **[사고 과정 훈련 예시]**
        *   **예시 1 (중간 빈칸):**
            *   **질문:** "참 빈칸 병원"
            *   **분석:** Prefix='참', Suffix='병원'.
            *   **이미지 내 단어:** '참좋은병원'
            *   **추론:** '참좋은병원'에서 '참'과 '병원'을 제거하면 **'좋은'** 이 남는다.
            *   **정답:** 좋은
        *   **예시 2 (시작 빈칸):**
            *   **질문:** "빈칸 원빌딩"
            *   **분석:** Prefix='', Suffix='원빌딩'.
            *   **이미지 내 단어:** '청원빌딩'
            *   **추론:** '청원빌딩'에서 '원빌딩'을 제거하면 **'청'** 이 남는다.
            *   **정답:** 청
        *   **예시 3 (끝 빈칸 - 가장 중요!):**
            *   **질문:** "참좋은병 빈칸"
            *   **분석:** Prefix='참좋은병', Suffix=''.
            *   **이미지 내 단어:** '참좋은병원'
            *   **추론:** '참좋은병원'에서 '참좋은병'을 제거하면 **'원'** 이 남는다.
            *   **정답:** 원
        *   **예시 4 (중간 빈칸):**
            *   **질문:** "청라빈칸PT"
            *   **분석:** Prefix='청라', Suffix='PT'.
            *   **이미지 내 단어:** '청라APT'
            *   **추론:** '청라APT'에서 '청라'와 'PT'을 제거하면 **'A'** 이 남는다.
            *   **정답:** A

        ---
        **[실제 문제 해결]**
        위의 핵심 원칙과 작업 절차를 완벽하게 따라서 아래 문제를 해결하세요.
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
