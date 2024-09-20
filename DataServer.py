import subprocess
import sys


# 패키지가 설치되지 않았을 경우 설치하는 함수
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


# 필요한 패키지 목록
required_packages = ["openai", "python-dotenv", "fastapi", "requests", "uvicorn", "python-multipart"]

# 패키지 설치 여부 확인 후 설치
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"{package} 패키지가 설치되어 있지 않습니다. 설치를 진행합니다.")
        install_package(package)

from fastapi import FastAPI, File, UploadFile
import os
from dotenv import load_dotenv
import requests
import json
import uuid
from openai import OpenAI
import time
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# FastAPI 앱 생성
app = FastAPI()

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7777"],  # 허용할 출처 (프론트엔드가 있는 도메인)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# .env 파일 로드
load_dotenv()

# 환경 변수 가져오기
clova_api_url = os.getenv("CLOVA_API_URL")
clova_secret_key = os.getenv("CLOVA_OCR_SECRET_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")


def call_clova_ocr(image_file):
    request_json = {
        'images': [{'format': 'jpg', 'name': 'receipt'}],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }

    headers = {'X-OCR-SECRET': clova_secret_key}
    files = [('file', image_file)]

    response = requests.post(clova_api_url, headers=headers, data={'message': json.dumps(request_json)}, files=files)

    if response.status_code == 200:
        ocr_result = response.json()
        return ''.join([field['inferText'] for field in ocr_result['images'][0]['fields']])
    else:
        raise Exception(f"Error: {response.status_code}")


def call_openai_food_and_expiration(text):
    # 첫 번째 OpenAI 호출: 식품 아이템 추출
    client = OpenAI(api_key=openai_api_key)
    ocr_response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system",
             "content": "Extract only food items and ingredients from the text, ignoring non-food items such as clothing, household items, and others. Return only the names of food products."},
            {"role": "user", "content": text}
        ]
    )

    food_items = list(map(lambda x: x.replace('-', '').strip(), ocr_response.choices[0].message.content.splitlines()))

    # 두 번째 OpenAI 호출: 각 식품에 대한 소비기한 추출
    if food_items:
        food_items_str = ', '.join(food_items)
        print(food_items_str)
        expiration_response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system",
                 "content": "For each food item listed, provide only the expiration date in days. No additional text is needed. For fresh products like milk and fruits, assign shorter expiration dates (e.g., 5), but for dry foods like snacks, ramen, frozen foods, jelly, and chocolate, assign longer expiration dates."},
                {"role": "user", "content": food_items_str}
            ]
        )

        # 두 번째 OpenAI 응답에서 소비기한 추출 및 유효성 검사
        expiration_dates_raw = expiration_response.choices[0].message.content.replace('\n', ',')
        expiration_dates = [int(x.strip()) if x.strip().isdigit() else 0 for x in expiration_dates_raw.split(',')]

        # 식품 이름과 소비기한을 딕셔너리로 결합
        result = dict(zip(food_items, expiration_dates))
    else:
        result = {}

    return result


@app.post("/ocr/")
async def upload_file(file: UploadFile = File(...)):
    # OCR 처리
    ocr_text = call_clova_ocr(file.file)
    # ocr_text = """로딩 중 \영수증 미지참시 교환/환불 불가
    # 정상상품에 한함, 30일 이내(신선 7일)
    # 교환/환불 구매점에서 가능(결제카드지참)
    # [구 매]2017-06-02 21:13 POS: 1021-5338
    # 상품명 단가 수량 금 액
    # 01* 노브랜드 굿밀크우 1,680 1 1,680
    # 02 스마트알뜰양복커버 2,590 1 2,590
    # 03 농심 포스틱 84g 1,120 1 1,120
    # 04 농심 올리브짜파게 3,850 1 3,850
    # 05* 산딸기 500g/박스 6,980 1 6,980
    # 06 (G)서핑여워터슈NY 19,800 1 19,800
    # 07 대여용부직포쇼핑백 500 1 500
    # 08* 호주곡물오이스터블 14,720 1 14,720
    # 09 오뚜기 콤비네이션 5,980 1 5,980
    # 10 꼬깔콘허니버터132G 1,580 1 1,580
    # 11 CJ미니드레싱골라담 3,980 1 3,980
    # 12 청정원허브맛솔트( 1,980 1 1,980
    # 13* 태국미니아스파라거 4,580 1 4,580
    # 14 롯데 수박바젤리 56 980 2 1,960
    # 15 바리스타 쇼콜라 32 2,250 1 2,250
    # (*) 면세 물품 27,960
    # 과세 물품 41,445
    # , 부 가 세 4,145
    # 합 계 73,550
    # 결제대상금액 73,550"""

    combined_result = call_openai_food_and_expiration(ocr_text)
    print(combined_result)

    return combined_result

class RecipeRequest(BaseModel):
    allergies: list
    ingredients: list

def call_openai_for_recommend(allergies, ingredients):
    # OpenAI API 호출을 위한 프롬프트 작성
    recommend_prompt = f"""
        사용자는 다음과 같은 음식 알레르기가 있습니다: {', '.join(allergies)}.
        사용 가능한 재료는 다음과 같습니다: {', '.join(ingredients)}.

        이 정보를 바탕으로 알레르기를 피하고, 주어진 재료를 활용한 요리법을 한국어로 추천해주세요.
        요리법은 정중하고 자세하게 설명해주세요.

        아래 형식에 맞춰 JSON 형식으로 요리법을 제공해주세요:

        {{
            "food_name": "요리 이름",
            "recipe": "1. 첫 번째 단계\\n2. 두 번째 단계\\n3. 세 번째 단계\\n...",
            "comment": "알레르기를 고려한 요리 설명"
        }}
        """

    client = OpenAI(api_key=openai_api_key)

    # OpenAI API 호출
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful chef."},
            {"role": "user", "content": recommend_prompt}
        ]
    )

    # OpenAI의 응답 받기
    recipe_recommendation = response.choices[0].message.content

    return recipe_recommendation


@app.post("/recipe-recommend/")
async def recipe_recommend(request: RecipeRequest):
    allergies = request.allergies
    ingredients = request.ingredients

    # OpenAI를 통해 요리법 추천 받기
    recipe_result = call_openai_for_recommend(allergies, ingredients)

    return {"recipe": recipe_result}
