import subprocess
import sys
from openai import OpenAI
import os
from dotenv import load_dotenv

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


def call_openai_for_recommend(allergies, ingredients):
    # 식단 추천 프롬프트 작성
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

    # recommend_prompt = f"""
    #     The user has the following food allergies: {', '.join(allergies)}.
    #     Available ingredients: {', '.join(ingredients)}.
    #
    #     Based on this information, please recommend a recipe that avoids the allergens and uses the available ingredients.
    #
    #     Please provide the response in the following JSON format:
    #
    #     {{
    #         "food_name": "Recipe name in Korean",
    #         "recipe": "1. Step one\\n2. Step two\\n3. Step three\\n...",
    #         "comment": "Provide a polite and detailed explanation in Korean, considering the allergies and ingredients."
    #     }}
    #
    #     The tone should be polite, respectful, and provide easy-to-follow, detailed instructions in Korean.
    #     """

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

# 예시 데이터
allergies = ['Eggs', 'Milk']  # 알러지 정보
ingredients = ['tomato', 'cheese', 'bread', 'onion', 'olive oil', 'basil', 'salt', 'pepper', 'garlic']

# OpenAI API를 통해 추천받기
recommended_recipe = call_openai_for_recommend(allergies, ingredients)
print(recommended_recipe)
