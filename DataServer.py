import subprocess
import sys

# 패키지가 설치되지 않았을 경우 설치하는 함수
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# 필요한 패키지 목록
required_packages = ["openai", "python-dotenv", "fastapi", "requests", "uvicorn","python-multipart"]

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

def call_openai_ocr(text):
    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system",
             "content": "Extract only food items and ingredients from the text, ignoring non-food items such as clothing, household items, and others. Return only the names of food products."},
            {"role": "user", "content": text}
        ]
    )
    # OpenAI의 응답을 JSON으로 변환
    openai_result = response.choices[0].message.content

    # 텍스트를 쉼표로 처리하여 배열로 만듭니다.
    ingredients = [f"{ingredient.strip().replace('-', '').strip()}" for ingredient in openai_result.splitlines() if ingredient.strip()]

    return ingredients
def call_openai_expiration_date(ingredients):
    # 식품 리스트를 기반으로 소비기한 요청을 위한 프롬프트 생성
    prompt = f"{', '.join(ingredients)}."

    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system",
             "content": "For each food item listed, provide only the expiration date in days. No additional text is needed. For fresh products like milk and fruits, assign shorter expiration dates (e.g., 5), but for dry foods like snacks, ramen, frozen foods, jelly, and chocolate, assign longer expiration dates."},
            {"role": "user", "content": prompt}
        ]
    )

    # OpenAI 응답을 그대로 반환
    openai_result = response.choices[0].message.content.replace('\n', ',')
    expiration_dates = [int(x) for x in openai_result.split(',') if x.strip().isdigit()]

    return expiration_dates

@app.post("/ocr/")
async def upload_file(file: UploadFile = File(...)):

    # OCR 처리
    #ocr_text = call_clova_ocr(file.file)
    ocr_text = """로딩 중 \영수증 미지참시 교환/환불 불가
    정상상품에 한함, 30일 이내(신선 7일)
    교환/환불 구매점에서 가능(결제카드지참)
    [구 매]2017-06-02 21:13 POS: 1021-5338
    상품명 단가 수량 금 액
    01* 노브랜드 굿밀크우 1,680 1 1,680
    02 스마트알뜰양복커버 2,590 1 2,590
    03 농심 포스틱 84g 1,120 1 1,120
    04 농심 올리브짜파게 3,850 1 3,850
    05* 산딸기 500g/박스 6,980 1 6,980
    06 (G)서핑여워터슈NY 19,800 1 19,800
    07 대여용부직포쇼핑백 500 1 500
    08* 호주곡물오이스터블 14,720 1 14,720
    09 오뚜기 콤비네이션 5,980 1 5,980
    10 꼬깔콘허니버터132G 1,580 1 1,580
    11 CJ미니드레싱골라담 3,980 1 3,980
    12 청정원허브맛솔트( 1,980 1 1,980
    13* 태국미니아스파라거 4,580 1 4,580
    14 롯데 수박바젤리 56 980 2 1,960
    15 바리스타 쇼콜라 32 2,250 1 2,250
    (*) 면세 물품 27,960
    과세 물품 41,445
    , 부 가 세 4,145
    합 계 73,550
    결제대상금액 73,550"""
    # OpenAI로 특정 키워드 추출
    ingredients = call_openai_ocr(ocr_text)
    #print(ingredients)

    expiration_dates = call_openai_expiration_date(ingredients)
    #print(expiration_dates)

    combined_result = dict(zip(ingredients, expiration_dates))
    print(combined_result)

    return combined_result
