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

def call_openai(text):
    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system", "content": "Extract only food items from the text."},
            {"role": "user", "content": text}
        ]
    )
    # OpenAI의 응답을 JSON으로 변환
    openai_result = response.choices[0].message.content

    # 텍스트를 쉼표로 처리하여 배열로 만듭니다.
    #ingredients = [ingredient.strip().replace('-', '').strip() for ingredient in openai_result.splitlines() if ingredient.strip()]
    ingredients = [f"{ingredient.strip().replace('-', '').strip()}" for ingredient in openai_result.splitlines() if ingredient.strip()]

    return {"ingredients": ingredients}  # JSON 배열 반환


@app.post("/ocr/")
async def upload_file(file: UploadFile = File(...)):

    # OCR 처리
    ocr_text = call_clova_ocr(file.file)

    # OpenAI로 특정 키워드 추출
    openai_result = call_openai(ocr_text)
    print(openai_result)
    return openai_result
