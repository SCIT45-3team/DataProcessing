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
    allow_origins=["*"],
    #allow_origins=["http://localhost:7777"],  # 허용할 출처 (프론트엔드가 있는 도메인)
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

################################# 영수증에서 식재료 추출 기능 #################################
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

    combined_result = call_openai_food_and_expiration(ocr_text)
    print(combined_result)

    return combined_result

################################# 보유한 재료를 가지고 레시피 추천 받는 기능 #################################
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
    print(recipe_result)

    return {"recipe": recipe_result}

################################# 신체 정보 + 식단 정보로 식단 밸런스 계산 기능 #################################

# 신체 정보와 식단을 받아 RDI를 계산하는 함수
def calculate_rdi_by_age_and_gender(age, gender):
    if gender == "M":
        if age < 30:
            return 2600  # 남성, 30세 미만
        elif age < 50:
            return 2400  # 남성, 30-50세
        else:
            return 2200  # 남성, 50세 이상
    else:
        if age < 30:
            return 2000  # 여성, 30세 미만
        elif age < 50:
            return 1800  # 여성, 30-50세
        else:
            return 1600  # 여성, 50세 이상

def calculate_RDI(height, weight, age, gender, activity_level=1.375):
    if gender == "M":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5  # 남성용 BMR 공식
    elif gender == "F":
        bmr = 10 * weight + 6.25 * height - 5 * age - 161  # 여성용 BMR 공식
    else:
        raise ValueError("Invalid gender. Use 'M' for Male or 'F' for Female.")

    rdi = bmr * activity_level
    return round(rdi, 2)

# OpenAI API 호출을 통한 영양 분석
def call_openai_for_nutrition(breakfast, lunch, dinner, age, gender, height=None, weight=None):
    if height is not None and weight is not None:
        rdi = calculate_RDI(height, weight, age, gender)
        body_info = f"Height: {height} cm, Weight: {weight} kg, Age: {age} years, Gender: {gender}, RDI: {rdi} kcal"
    else:
        rdi = calculate_rdi_by_age_and_gender(age, gender)
        body_info = f"Age: {age} years, Gender: {gender}, RDI: {rdi} kcal"

    meals = f"Breakfast: {breakfast}, Lunch: {lunch}, Dinner: {dinner}"

    nutrition_prompt = f"""
                                    You are a nutrition assistant. The user has the following physical attributes:
                                    {body_info}
                                    The user has consumed the following meals throughout the day:
                                    {meals}.

                                    Based on this, provide the following analysis in **one JSON object**:

                                    1. Provide the estimated calories for each meal and the total calories for the day. Ensure the response includes only numeric values for calories.
                                    2. Identify any nutrients that were excessively consumed (e.g., carbohydrates, protein, fat, saturated fat, trans fat, sodium, cholesterol, sugars, fiber, vitamins (A, C, D, E, K, B12, B6), minerals (calcium, iron, magnesium, phosphorus, potassium, zinc), omega-3 fatty acids). Ensure the response includes only the nutrient names in **an array format** in Korean (e.g., ["지방", "나트륨"]).
                                    3. Identify any nutrients that were lacking (e.g., carbohydrates, protein, fat, saturated fat, trans fat, sodium, cholesterol, sugars, fiber, vitamins (A, C, D, E, K, B12, B6), minerals (calcium, iron, magnesium, phosphorus, potassium, zinc), omega-3 fatty acids) based on the daily recommended intake. Ensure the response includes only the nutrient names in **an array format** in Korean.
                                    4. Suggest specific foods or ingredients the user can consume to **replenish the lacking nutrients** and **reduce the excessive nutrients**. The suggestion should be formatted like this: **"[음식 목록]을 섭취하여 [lacking_nutrients]를 보충하는 것을 권장합니다."** Ensure that the foods recommended specifically address the identified lacking nutrients while avoiding those that contribute to the excess.
                                    5. Give an overall score for the day’s meals on a scale of 1 to 100, considering nutritional balance and healthiness. Provide the score as a numeric value.

                                    Ensure that the response is entirely in Korean, in the following **JSON format**:

                                    {{
                                      "kal": {{
                                        "b": [칼로리 숫자],
                                        "l": [칼로리 숫자],
                                        "d": [칼로리 숫자],
                                        "t": [총 칼로리 숫자],
                                        "RDI": {rdi}
                                      }},
                                      "over": [과잉 섭취된 영양소 목록 배열],
                                      "lack": [부족한 영양소 목록 배열],
                                      "rec": "당신의 일일 권장 섭취량인 [RDI] kcal를 고려했을 때, 과잉 섭취된 영양소는 줄이고 부족한 영양소를 보충하기 위해 [음식 목록]을 섭취하는 것을 권장합니다.",
                                      "score": [점수]
                                    }}

                                    Make sure the response is strictly in Korean and follows this JSON structure without any additional explanations.
                                """
    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful nutritionist."},
            {"role": "user", "content": nutrition_prompt}
        ]
    )
    nutrition_analysis = response.choices[0].message.content
    return nutrition_analysis

# 사용자의 신체 정보와 식단을 입력받는 FastAPI 모델
from typing import Optional

class NutritionRequest(BaseModel):
    age: int
    gender: str
    height: Optional[float] = None  # None 허용
    weight: Optional[float] = None  # None 허용
    breakfast: Optional[str] = None  # None 허용
    lunch: Optional[str] = None  # None 허용
    dinner: Optional[str] = None  # None 허용

# 영양 분석 엔드포인트 생성
@app.post("/nutrition/")
async def nutrition_analysis(request: NutritionRequest):
    breakfast = request.breakfast if request.breakfast is not None else ""
    lunch = request.lunch if request.lunch is not None else ""
    dinner = request.dinner if request.dinner is not None else ""

    result = call_openai_for_nutrition(
        breakfast=breakfast,
        lunch=lunch,
        dinner=dinner,
        age=request.age,
        gender=request.gender,
        height=request.height,
        weight=request.weight
    )
    print(result)
    try:
        parsed_result = json.loads(result)  # 문자열을 JSON으로 변환
        return parsed_result
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return {"error": "Invalid JSON format returned from OpenAI"}


