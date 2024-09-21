# import subprocess
# import sys
#
# # 패키지가 설치되지 않았을 경우 설치하는 함수
# def install_package(package):
#     subprocess.check_call([sys.executable, "-m", "pip", "install", package])
#
# # 필요한 패키지 목록
# required_packages = ["openai", "python-dotenv"]
#
# # 패키지 설치 여부 확인 후 설치
# for package in required_packages:
#     try:
#         __import__(package)
#     except ImportError:
#         print(f"{package} 패키지가 설치되어 있지 않습니다. 설치를 진행합니다.")
#         install_package(package)
#
# # 필요한 패키지들 불러오기
# from openai import OpenAI
# import os
# from dotenv import load_dotenv
#
# # .env 파일에서 환경 변수 로드
# load_dotenv()
#
# # OpenAI API 키 설정
# openai_api_key = os.getenv("OPENAI_API_KEY")
#
# def call_openai_for_nutrition(breakfast, lunch, dinner):
#     # 식단 정보 설정
#     meals = f"Breakfast: {breakfast}, Lunch: {lunch}, Dinner: {dinner}"
#
#     nutrition_prompt = f"""
#                             You are a nutrition assistant. The user has consumed the following meals throughout the day:
#                             Breakfast: {breakfast}, Lunch: {lunch}, Dinner: {dinner}.
#
#                             Based on this entire day's meals, provide the following analysis in **one JSON object**:
#
#                             1. Provide the estimated calories for each meal and the total calories for the day. Ensure the response includes only numeric values for calories.
#                             2. Identify any nutrients that were excessively consumed (e.g., carbohydrates, protein, fat, saturated fat, trans fat, sodium, cholesterol, sugars, fiber, vitamins (A, C, D, E, K, B12, B6), minerals (calcium, iron, magnesium, phosphorus, potassium, zinc), omega-3 fatty acids). Ensure the response includes only the nutrient names in **an array format** in Korean (e.g., ["지방", "나트륨"]).
#                             3. Identify any nutrients that were lacking (e.g., carbohydrates, protein, fat, saturated fat, trans fat, sodium, cholesterol, sugars, fiber, vitamins (A, C, D, E, K, B12, B6), minerals (calcium, iron, magnesium, phosphorus, potassium, zinc), omega-3 fatty acids) based on the daily recommended intake. Ensure the response includes only the nutrient names in **an array format** in Korean.
#                             4. Suggest specific foods or ingredients the user can consume to **replenish the lacking nutrients** and **reduce the excessive nutrients**. The suggestion should be formatted like this: **"[음식 목록]을 섭취하여 [lacking_nutrients]를 보충하는 것을 권장합니다."** Ensure that the foods recommended specifically address the identified lacking nutrients while avoiding those that contribute to the excess.
#                             5. Give an overall score for the day’s meals on a scale of 1 to 100, considering nutritional balance and healthiness. Provide the score as a numeric value.
#
#                             Ensure that the response is entirely in Korean, in the following **JSON format**:
#
#                             {{
#                               "kal": {{
#                                 "b": [칼로리 숫자],
#                                 "l": [칼로리 숫자],
#                                 "d": [칼로리 숫자],
#                                 "t": [총 칼로리 숫자]
#                               }},
#                               "over": [과잉 섭취된 영양소 목록 배열],
#                               "lack": [부족한 영양소 목록 배열],
#                               "rec": "[음식 목록]을 섭취하여 [lacking_nutrients]를 보충하는 것을 권장합니다",
#                               "score": [점수]
#                             }}
#
#                             Make sure the response is strictly in Korean and follows this JSON structure without any additional explanations.
#                         """
#
#     client = OpenAI(api_key=openai_api_key)
#
#     # OpenAI API 호출
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "You are a helpful nutritionist."},
#             {"role": "user", "content": nutrition_prompt}
#         ]
#     )
#
#     # OpenAI의 응답 받기
#     nutrition_analysis = response.choices[0].message.content
#
#     return nutrition_analysis
#
#
# # 사용 예시
# breakfast = "김치찌개"
# lunch = "치즈버거"
# dinner = ""
#
# nutrition_info = call_openai_for_nutrition(breakfast, lunch, dinner)
# print(nutrition_info)


import subprocess
import sys
import os
from dotenv import load_dotenv
from openai import OpenAI


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

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정
openai_api_key = os.getenv("OPENAI_API_KEY")


def calculate_rdi_by_age_and_gender(age, gender):
    # 나이와 성별에 따른 기본 일일 권장 섭취량 (칼로리)
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
    """
    RDI(Reference Daily Intake)를 계산하는 함수.

    Parameters:
    - height: 키 (cm)
    - weight: 몸무게 (kg)
    - age: 나이 (years)
    - gender: 성별 ("M" for Male, "F" for Female)
    - activity_level: 활동 수준 계수 (default는 가벼운 활동)

    Returns:
    - RDI: 계산된 일일 권장 칼로리 섭취량 (kcal)
    """
    # Mifflin-St Jeor Equation을 사용한 BMR 계산
    if gender == "M":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5  # 남성용 BMR 공식
    elif gender == "F":
        bmr = 10 * weight + 6.25 * height - 5 * age - 161  # 여성용 BMR 공식
    else:
        raise ValueError("Invalid gender. Use 'M' for Male or 'F' for Female.")

    # 활동 계수에 따른 RDI 계산
    rdi = bmr * activity_level

    return round(rdi, 2)  # 소수점 두 자리까지 반올림하여 반환


def call_openai_for_nutrition(breakfast, lunch, dinner, age, gender, height=None, weight=None):
    """
    OpenAI API를 호출하여 식단 분석 및 RDI 기반 영양소 권장 분석을 수행하는 함수.

    Parameters:
    - breakfast: 아침 식사 정보
    - lunch: 점심 식사 정보
    - dinner: 저녁 식사 정보
    - height: 사용자의 키 (optional)
    - weight: 사용자의 몸무게 (optional)
    - age: 사용자의 나이 (필수)
    - gender: 사용자의 성별 (필수)

    Returns:
    - nutrition_analysis: OpenAI의 식단 분석 결과 (JSON 형식)
    """
    # 신체 정보가 제공되지 않은 경우 나이와 성별을 기준으로 RDI 계산
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
lunch = "삼겹살"
dinner = "제육볶음"
height = 175
weight = None
age = 29
gender = "M"

# OpenAI API 호출 및 식단 분석
nutrition_info = call_openai_for_nutrition(breakfast, lunch, dinner, age, gender, height, weight)
print(nutrition_info)

