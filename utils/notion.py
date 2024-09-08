import asyncio
from notion_client import AsyncClient  # 비동기 클라이언트 사용
from dotenv import load_dotenv
from pprint import pprint
import os
from enum import Enum
from typing import List, Dict, Any, Union, Optional

from utils.condition import Condition

# Enum 클래스 정의
class ROLES(str, Enum):
    DEVREL = "💝 DevRel (Developer Relations)"
    DESIGNER = "🎨 Designer"
    SWE = "🖥️ SWE (Software Engineer)"

class ROLES_DEVREL(str, Enum):
    DE = "✍️ DE (Developer Educator)"
    CB = "👪 CB (Community Builder)"

class TIER(str, Enum):
    JUNIOR = "🌱 Junior"
    MEMBER = "👥 Member"
    CORE = "🔥 Core Member"
    DEVREL_LEAD = "⭐ DevRel Lead"
    LEAD = "⭐ Lead"

NOTION_MEMBER_DB_PROPERTIES = ['Discord ID', '희망 직군 (SWE)', '출석 행사', '입학 년도', '티어 (DevRel)', '티어 (SWE)', '티어 (Designer)', 'GitHub (SWE)', '등록 행사', '활동 분야 (DevRel)', 'branch/junior 이수 여부', 'branch/git 등록', '전화번호', '결석 행사', '전공', '영문 성명', '이중/심화/융합/복수 전공', '이메일', '학번', '이름', '활동 분야']


async def find_members_in_notion(notion: AsyncClient, condition: Condition, 
                                 database_id: str,
                                 tier: Optional[TIER] = None, 
                                 name: Optional[str] = None, 
                                 discord_id: Optional[Union[str, int]] = None,
                                 role: Optional[ROLES] = None) -> Dict[str, Any]:
    """
    Notion 데이터베이스에서 티어, 이름, 역할 등 여러 조건을 선택적으로 사용할 수 있는 멤버 검색 함수.
    
    :param notion: Notion 비동기 API 클라이언트 객체
    :param condition: Condition 객체, Notion 필터 조건 생성에 사용
    :param database_id: 멤버 데이터베이스 id
    :param tier: Optional 티어 조건 (TIER Enum)
    :param name: Optional 이름 조건 (string)
    :param discord_id: Optional 디스코드 ID 조건 (string 또는 int)
    :param role: Optional 역할 조건 (ROLES Enum)
    :return: 검색 결과를 포함한 딕셔너리
    """
    filters = {}
    
    # 주어진 조건에 따라 필터를 동적으로 추가
    if tier:
        filters['티어 (SWE)'] = tier.value
    if name:
        filters['이름'] = f"contains {name}"
    if discord_id:
        discord_id = str(discord_id) if isinstance(discord_id, int) else discord_id
        filters['Discord ID'] = discord_id
    if role:
        filters['활동 분야'] = role.value
    
    # 필터가 주어진 경우에만 조건 생성
    if filters:
        cond = condition(filters)
        result = await notion.databases.query(database_id=database_id, filter=cond.get_filters())  # 비동기 호출
    else:
        raise ValueError("At least one condition must be provided.")
    
    return result


async def search_members_in_database(notion: AsyncClient, database_id: str, 
                                                 conditions_list: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    데이터베이스 ID와 여러 조건 목록을 받아, 각 조건에 맞는 멤버 정보를 비동기적으로 병렬 처리하여 반환하는 함수.

    :param notion: Notion 비동기 API 클라이언트 객체
    :param database_id: 검색할 Notion 데이터베이스 ID
    :param conditions_list: 검색할 조건들의 목록 (각 dict는 티어, 이름, role, discord_id 등을 포함)
    :return: 각 조건에 따른 검색 결과를 리스트 형식으로 반환
    """
    
    # Notion에서 데이터베이스 목록 가져오기
    databases = await notion.search(filter={"property": "object", "value": "database"})
    
    # 입력된 데이터베이스 ID와 일치하는 데이터베이스를 찾기 (ID에서 '-' 제거)
    target_db_id = database_id.replace("-", "")
    target_db = None
    for db in databases['results']:
        db_id_cleaned = db['id'].replace("-", "")
        if db_id_cleaned == target_db_id:
            target_db = db
            break
    
    if not target_db:
        raise ValueError(f"Database with ID {database_id} not found.")
    
    # 조건 필터 객체 초기화
    condition = Condition(target_db["properties"])
    
    # 비동기적으로 여러 조건을 처리
    async def process_single_condition(cond: Dict[str, Any]) -> List[Dict[str, Any]]:
        tier = cond.get('tier')
        name = cond.get('name')
        discord_id = cond.get('discord_id')
        role = cond.get('role')
        
        # 멤버 검색 수행
        result = await find_members_in_notion(
            notion=notion,
            condition=condition,
            database_id=database_id,
            tier=tier,
            name=name,
            discord_id=discord_id,
            role=role
        )
        return result['results']
    
    # 모든 조건을 비동기적으로 실행
    tasks = [process_single_condition(cond) for cond in conditions_list]
    results = await asyncio.gather(*tasks)
    
    # 결과 리스트 반환
    return results

def format_notion_member_info(member_data: Dict[str, Any], prefix: str = "-") -> str:
    """
    Notion 검색 결과를 사용자에게 읽기 쉬운 형식으로 변환하는 함수.
    정보를 추출하고, 존재하는 정보만 포함하도록 구성.
    
    :param member_data: Notion에서 반환된 멤버 정보 (dict 형식)
    :param prefix: 각 정보 항목 앞에 붙일 접두어 (기본값: '-')
    :return: 예쁘게 포맷된 문자열
    """
    properties = member_data.get("properties", {})
    
    # 정보 추출 (존재하지 않으면 None을 반환)
    def extract_rich_text(key):
        return properties.get(key, {}).get("rich_text", [{}])[0].get("plain_text", None)

    def extract_title(key):
        return properties.get(key, {}).get("title", [{}])[0].get("plain_text", None)

    def extract_multi_select(key):
        # multi_select가 빈 리스트일 경우, 첫 번째 항목을 가져오지 않음
        multi_select = properties.get(key, {}).get("multi_select", [])
        return multi_select[0].get("name", None) if multi_select else None

    name = extract_title("이름")
    discord_id = extract_rich_text("Discord ID")
    email = extract_rich_text("이메일")
    github = extract_rich_text("GitHub (SWE)")
    phone = extract_rich_text("전화번호")
    tier_swe = extract_multi_select("티어 (SWE)")
    tier_devrel = extract_multi_select("티어 (DevRel)")
    tier_designer = extract_multi_select("티어 (Designer)")
    role = ', '.join([r.get("name", "") for r in properties.get("활동 분야", {}).get("multi_select", [])]) or None
    major = extract_rich_text("전공")
    student_id = extract_rich_text("학번")
    
    # 포맷할 정보 목록
    info = []
    
    # 값이 있는 경우에만 추가
    if name: info.append(f"{prefix} **이름**: {name}")
    if major: info.append(f"{prefix} **전공**: {major}")
    if student_id: info.append(f"{prefix} **학번**: {student_id}")
    if discord_id: info.append(f"{prefix} **Discord ID**: {discord_id}")
    if email: info.append(f"{prefix} **이메일**: {email}")
    if github: info.append(f"{prefix} **GitHub**: {github}")
    if phone: info.append(f"{prefix} **전화번호**: {phone}")
    if tier_swe: info.append(f"{prefix} **SWE 티어**: {tier_swe}")
    if tier_devrel: info.append(f"{prefix} **DevRel 티어**: {tier_devrel}")
    if tier_designer: info.append(f"{prefix} **Designer 티어**: {tier_designer}")
    if role: info.append(f"{prefix} **역할**: {role}")

    
    # 존재하는 정보만을 포함한 포맷팅된 문자열 반환
    return '\n'.join(info) if info else "정보가 없습니다."



# async def main():
#     notion = AsyncClient(auth=NOTION_API_KEY)
    
#     # 검색할 조건들 (리스트 형식으로 여러 조건)
#     conditions_list = [
#         {'discord_id': 122},
#         {'tier': TIER.MEMBER},
#         {'name': "전성후"}
#     ]

#     # 데이터베이스 ID
#     database_id = NOTION_MEMBER_DB_ID

#     # 멤버 검색 함수 호출
#     results = await search_members_in_database(notion, database_id, conditions_list)
    
#     # 결과 출력
#     for i, result in enumerate(results):
#         print(f"검색 조건 {i+1}에 대한 결과: {len(result)}명의 멤버")


# if __name__ == "__main__":
#     # Load environment variables from .env file
#     load_dotenv()

#     # Retrieve values from environment variables
#     DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
#     NOTION_API_KEY = os.getenv("NOTION_API_KEY")
#     NOTION_MEMBER_DB_ID = os.getenv("NOTION_MEMBER_DB_ID")
#     NOTION_SCHEDULE_DB_ID = os.getenv("NOTION_SCHEDULE_DB_ID")  

#     # 비동기 실행
#     asyncio.run(main())

async def find_schedule_in_notion(notion: AsyncClient, condition: Condition, 
                                 database_id: str,
                                 name: Optional[str] = None, 
                                 tag: Optional[str] = None) -> Dict[str, Any]:
    """
    Notion 데이터베이스에서 이름, 태그 등 여러 조건을 선택적으로 사용할 수 있는 스케줄 검색 함수.
    
    :param notion: Notion 비동기 API 클라이언트 객체
    :param condition: Condition 객체, Notion 필터 조건 생성에 사용
    :param database_id: 멤버 데이터베이스 id
    :param tier: Optional 티어 조건 (TIER Enum)
    :param name: Optional 이름 조건 (string)
    :param discord_id: Optional 디스코드 ID 조건 (string 또는 int)
    :param role: Optional 역할 조건 (ROLES Enum)
    :return: 검색 결과를 포함한 딕셔너리
    """
    filters = {}
    
    # 주어진 조건에 따라 필터를 동적으로 추가x
    if name:
        filters['이름'] = f"contains {name}"
    if tag:
        filters['태그'] = tag
    
    # 필터가 주어진 경우에만 조건 생성
    if filters:
        cond = condition(filters)
        result = await notion.databases.query(database_id=database_id, filter=cond.get_filters())  # 비동기 호출
    else:
        raise ValueError("At least one condition must be provided.")
    
    return result


async def search_schedules_in_database(notion: AsyncClient, database_id: str, 
                                                 conditions_list: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    데이터베이스 ID와 여러 조건 목록을 받아, 각 조건에 맞는 멤버 정보를 비동기적으로 병렬 처리하여 반환하는 함수.

    :param notion: Notion 비동기 API 클라이언트 객체
    :param database_id: 검색할 Notion 데이터베이스 ID
    :param conditions_list: 검색할 조건들의 목록 (각 dict는 티어, 이름, role, discord_id 등을 포함)
    :return: 각 조건에 따른 검색 결과를 리스트 형식으로 반환
    """
    
    # Notion에서 데이터베이스 목록 가져오기
    databases = await notion.search(filter={"property": "object", "value": "database"})
    
    # 입력된 데이터베이스 ID와 일치하는 데이터베이스를 찾기 (ID에서 '-' 제거)
    target_db_id = database_id.replace("-", "")
    target_db = None
    for db in databases['results']:
        db_id_cleaned = db['id'].replace("-", "")
        if db_id_cleaned == target_db_id:
            target_db = db
            break
    
    if not target_db:
        raise ValueError(f"Database with ID {database_id} not found.")
    
    # 조건 필터 객체 초기화
    condition = Condition(target_db["properties"])
    
    # 비동기적으로 여러 조건을 처리
    async def process_single_condition(cond: Dict[str, Any]) -> List[Dict[str, Any]]:
        name = cond.get('name')
        tag = cond.get('tag')
        
        # 멤버 검색 수행
        result = await find_schedule_in_notion(
            notion=notion,
            condition=condition,
            database_id=database_id,
            name=name,
            tag=tag,
        )
        return result['results']
    
    # 모든 조건을 비동기적으로 실행
    tasks = [process_single_condition(cond) for cond in conditions_list]
    results = await asyncio.gather(*tasks)
    
    # 결과 리스트 반환
    return results


