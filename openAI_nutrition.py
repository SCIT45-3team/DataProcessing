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
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정
openai_api_key = os.getenv("OPENAI_API_KEY")

def call_openai_for_nutrition(breakfast, lunch, dinner):
    # 식단 정보 설정
    meals = f"Breakfast: {breakfast}, Lunch: {lunch}, Dinner: {dinner}"

    nutrition_prompt = f"""
                            You are a nutrition assistant. The user has consumed the following meals throughout the day:
                            Breakfast: {breakfast}, Lunch: {lunch}, Dinner: {dinner}.

                            Based on this entire day's meals, provide the following analysis in **one JSON object**:

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
                                "t": [총 칼로리 숫자]
                              }},
                              "over": [과잉 섭취된 영양소 목록 배열],
                              "lack": [부족한 영양소 목록 배열],
                              "rec": "[음식 목록]을 섭취하여 [lacking_nutrients]를 보충하는 것을 권장합니다",
                              "score": [점수]
                            }}

                            Make sure the response is strictly in Korean and follows this JSON structure without any additional explanations.
                        """

    client = OpenAI(api_key=openai_api_key)

    # OpenAI API 호출
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful nutritionist."},
            {"role": "user", "content": nutrition_prompt}
        ]
    )

    # OpenAI의 응답 받기
    nutrition_analysis = response.choices[0].message.content

    return nutrition_analysis


# 사용 예시
breakfast = "김치찌개"
lunch = "치즈버거"
dinner = ""

nutrition_info = call_openai_for_nutrition(breakfast, lunch, dinner)
print(nutrition_info)
