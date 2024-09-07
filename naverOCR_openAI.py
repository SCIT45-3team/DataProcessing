import subprocess
import sys

# 패키지가 설치되지 않았을 경우 설치하는 함수
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# 필요한 패키지 목록
required_packages = ["openai", "python-dotenv"]

# 패키지 설치 여부 확인 후 설치
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"{package} 패키지가 설치되어 있지 않습니다. 설치를 진행합니다.")
        install_package(package)

# 필요한 패키지들 불러오기
from openai import OpenAI
import json
import requests
import uuid
import time
import os
from dotenv import load_dotenv


# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수 가져오기
clova_api_url = os.getenv("CLOVA_API_URL")
clova_secret_key = os.getenv("CLOVA_OCR_SECRET_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

def call_clova_ocr(image_file):
    # OCR 요청 JSON 구성
    request_json = {
        'images': [
            {
                'format': 'jpg',
                'name': 'receipt'
            }
        ],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }

    # 파일 업로드를 위한 payload 구성
    payload = {'message': json.dumps(request_json).encode('UTF-8')}
    files = [
        ('file', open(image_file, 'rb'))
    ]
    headers = {
        'X-OCR-SECRET': clova_secret_key
    }

    # POST 요청
    response = requests.post(clova_api_url, headers=headers, data=payload, files=files)

    if response.status_code == 200:
        json_data = response.json()

        # 응답 내용을 영수증 형태로 변환
        string_result = ''
        for i in json_data['images'][0]['fields']:
            linebreak = '\n' if i['lineBreak'] else ' '
            string_result += i['inferText'] + linebreak

        return string_result
    else:
        raise Exception(f"Error in OCR request: {response.status_code}, {response.text}")


# 사용 예시
image_file = 'receipt.jpeg'

#string_result = call_clova_ocr(image_file)
string_result = """로딩 중 \영수증 미지참시 교환/환불 불가
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

client = OpenAI(api_key=openai_api_key)

# ChatGPT 호출
response = client.chat.completions.create(
    model="gpt-3.5-turbo-1106",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system",
         "content": "You are a helpful assistant to analyze the items from the receipt and output only the food ingredient items in JSON format."},
        {"role": "user",
         "content": f"please analyze {string_result}. only extract food ingredient items. If an item is free, set its cost to 0."}
    ]
)

# ChatGPT 회신
message = response.choices[0].message.content
print(message)


