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
                                 role: Optional[ROLES] = None) -> List[Dict[str, Any]]:
    """
    Notion 데이터베이스에서 티어, 이름, 역할 등 여러 조건을 선택적으로 사용할 수 있는 멤버 검색 함수.
    페이지네이션을 처리하여 모든 결과를 반환합니다.
    
    :param notion: Notion 비동기 API 클라이언트 객체
    :param condition: Condition 객체, Notion 필터 조건 생성에 사용
    :param database_id: 멤버 데이터베이스 id
    :param tier: Optional 티어 조건 (TIER Enum)
    :param name: Optional 이름 조건 (string)
    :param discord_id: Optional 디스코드 ID 조건 (string 또는 int)
    :param role: Optional 역할 조건 (ROLES Enum)
    :return: 검색 결과를 포함한 딕셔너리 리스트
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
    
    if filters:
        cond = condition(filters)
        result_list = []
        start_cursor = None
        has_more = True
        
        while has_more:
            result = await notion.databases.query(
                database_id=database_id, 
                filter=cond.get_filters(),
                start_cursor=start_cursor,
            )
            result_list.extend(result['results'])
            has_more = result.get('has_more', False)
            start_cursor = result.get('next_cursor', None)
            
        return result_list
    
    else:
        raise ValueError("At least one condition must be provided.")


async def find_schedule_in_notion(notion: AsyncClient, condition: Condition, 
                                  database_id: str,
                                  name: Optional[str] = None, 
                                  tag: Optional[str] = None,
                                  date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Notion 데이터베이스에서 이름, 태그 등 여러 조건을 선택적으로 사용할 수 있는 스케줄 검색 함수.
    페이지네이션을 처리하여 모든 결과를 반환합니다.
    
    :param notion: Notion 비동기 API 클라이언트 객체
    :param condition: Condition 객체, Notion 필터 조건 생성에 사용
    :param database_id: 스케줄 데이터베이스 ID
    :param name: Optional 이름 조건 (string)
    :param tag: Optional 태그 조건 (string)
    :param date: Optional 날짜 조건 (string)
    :return: 검색 결과를 포함한 딕셔너리 리스트
    """
    filters = {}
    
    # 주어진 조건에 따라 필터를 동적으로 추가
    if name:
        filters['이름'] = f"contains {name}"
    if tag:
        filters['태그'] = tag
    if date:
        filters['날짜'] = date
    
    if filters:
        cond = condition(filters)
        result_list = []
        start_cursor = None
        has_more = True
        
        while has_more:
            result = await notion.databases.query(
                database_id=database_id, 
                filter=cond.get_filters(),
                sorts=[
                    {
                        'property': "날짜",
                        'direction': 'ascending'
                    }
                ],
                start_cursor=start_cursor,
            )
            result_list.extend(result['results'])
            has_more = result.get('has_more', False)
            start_cursor = result.get('next_cursor', None)
            
        return result_list
    else:
        raise ValueError("At least one condition must be provided.")


async def search_members_in_database(notion: AsyncClient, database_id: str, 
                                     conditions_list: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    데이터베이스 ID와 여러 조건 목록을 받아, 각 조건에 맞는 멤버 정보를 비동기적으로 병렬 처리하여 반환하는 함수.
    페이지네이션을 처리하여 모든 결과를 반환합니다.

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
        return result
    
    # 모든 조건을 비동기적으로 실행
    tasks = [process_single_condition(cond) for cond in conditions_list]
    results = await asyncio.gather(*tasks)
    
    return results


async def search_schedules_in_database(notion: AsyncClient, database_id: str, 
                                       conditions_list: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    데이터베이스 ID와 여러 조건 목록을 받아, 각 조건에 맞는 스케줄 정보를 비동기적으로 병렬 처리하여 반환하는 함수.
    페이지네이션을 처리하여 모든 결과를 반환합니다.

    :param notion: Notion 비동기 API 클라이언트 객체
    :param database_id: 검색할 Notion 데이터베이스 ID
    :param conditions_list: 검색할 조건들의 목록 (각 dict는 이름, 태그, 날짜 등을 포함)
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
        date = cond.get('date')

        # 스케줄 검색 수행
        result = await find_schedule_in_notion(
            notion=notion,
            condition=condition,
            database_id=database_id,
            name=name,
            tag=tag,
            date=date,
        )
        return result
    
    # 모든 조건을 비동기적으로 실행
    tasks = [process_single_condition(cond) for cond in conditions_list]
    results = await asyncio.gather(*tasks)
    
    return results


def safe_extract(properties: Dict[str, Any], key: str, extract_type: str) -> Optional[Union[str, List[str]]]:
    """
    Notion 데이터에서 안전하게 값을 추출하는 함수.
    
    :param properties: Notion에서 반환된 properties 딕셔너리
    :param key: 추출할 속성의 키
    :param extract_type: 추출할 데이터의 유형 (title, rich_text, date, relation, multi_select)
    :return: 추출된 값 또는 None
    """
    try:
        if extract_type == "title":
            return properties.get(key, {}).get("title", [{}])[0].get("plain_text", None)
        elif extract_type == "rich_text":
            return properties.get(key, {}).get("rich_text", [{}])[0].get("plain_text", None)
        elif extract_type == "date":
            return properties.get(key, {}).get("date", {}).get("start", None)
        elif extract_type == "relation":
            return [relation.get("id") for relation in properties.get(key, {}).get("relation", [])]
        elif extract_type == "multi_select":
            return ', '.join([tag.get("name", "") for tag in properties.get(key, {}).get("multi_select", [])])
    except (KeyError, IndexError, AttributeError):
        return None
    return None


def format_notion_member_info(member_data: Dict[str, Any], prefix: str = "-") -> str:
    """
    Notion 멤버 정보를 사용자에게 읽기 쉬운 형식으로 변환하는 함수.
    
    :param member_data: Notion에서 반환된 멤버 정보 (dict 형식)
    :param prefix: 각 정보 항목 앞에 붙일 접두어 (기본값: '-')
    :return: 예쁘게 포맷된 문자열
    """
    properties = member_data.get("properties", {})
    
    # 멤버 정보 추출
    name = safe_extract(properties, "이름", "title")
    discord_id = safe_extract(properties, "Discord ID", "rich_text")
    email = safe_extract(properties, "이메일", "rich_text")
    github = safe_extract(properties, "GitHub (SWE)", "rich_text")
    phone = safe_extract(properties, "전화번호", "rich_text")
    tier_swe = safe_extract(properties, "티어 (SWE)", "multi_select")
    tier_devrel = safe_extract(properties, "티어 (DevRel)", "multi_select")
    tier_designer = safe_extract(properties, "티어 (Designer)", "multi_select")
    role = safe_extract(properties, "활동 분야", "multi_select")
    major = safe_extract(properties, "전공", "rich_text")
    student_id = safe_extract(properties, "학번", "rich_text")
    notion_id = member_data.get("id")


    # 포맷할 정보 목록
    info = []

    # 값이 있는 경우에만 추가
    if notion_id: info.append(f"{prefix} **노션 ID**: {notion_id}")
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


def format_notion_schedule_info(schedule_data: Dict[str, Any], prefix: str = "-", return_notion_id=True) -> str:
    """
    Notion 일정 정보를 사용자에게 읽기 쉬운 형식으로 변환하는 함수.
    
    :param schedule_data: Notion에서 반환된 일정 정보 (dict 형식)
    :param prefix: 각 정보 항목 앞에 붙일 접두어 (기본값: '-')
    :return: 예쁘게 포맷된 문자열
    """
    properties = schedule_data.get("properties", {})
    
    # 일정 정보 추출
    notion_id = schedule_data.get("id")
    name = safe_extract(properties, "이름", "title")
    date = safe_extract(properties, "날짜", "date")
    location = safe_extract(properties, "장소", "rich_text")
    # attendees = safe_extract(properties, "출석자 (인정 결석 포함)", "relation")
    # absentees = safe_extract(properties, "결석자", "relation")
    # tags = safe_extract(properties, "태그", "multi_select")
    # parent = safe_extract(properties, "상위 항목", "relation")



    # 포맷할 정보 목록
    info = []

    # 값이 있는 경우에만 추가
    if notion_id and return_notion_id: info.append(f"{prefix} **노션 ID**: {notion_id}")
    if name: info.append(f"{prefix} **이름**: {name}")
    if date: info.append(f"{prefix} **날짜**: {date}")
    if location: info.append(f"{prefix} **장소**: {location}")
    # if attendees: info.append(f"{prefix} **출석자**: {', '.join(attendees)}")
    # if absentees: info.append(f"{prefix} **결석자**: {', '.join(absentees)}")
    # if tags: info.append(f"{prefix} **태그**: {tags}")
    # if parent: info.append(f"{prefix} **상위 항목**: {', '.join(parent)}")


    # 존재하는 정보만을 포함한 포맷팅된 문자열 반환
    return '\n'.join(info) if info else "일정 정보가 없습니다."




async def _extract_property_from_page_id(notion: AsyncClient, page_id: str, property_id: str) -> List[Dict[str, Any]]:
    """
    단일 page_id에 대해 단일 property_id로 속성을 추출하는 함수.
    페이지네이션을 지원하여 모든 데이터를 가져옵니다.
    
    :param notion: Notion 비동기 클라이언트
    :param page_id: Notion 페이지 ID
    :param property_id: 추출할 속성 ID
    :return: 추출된 속성 값 리스트
    """
    properties = []
    has_more = True
    start_cursor = None

    while has_more:
        result = await notion.pages.properties.retrieve(
            page_id=page_id, 
            property_id=property_id, 
            start_cursor=start_cursor
        )

        # 결과 값을 저장
        if 'results' in result:
            properties.extend(result['results'])
        
        # 다음 페이지가 있는지 확인
        has_more = result.get('has_more', False)
        start_cursor = result.get('next_cursor', None)

    return properties

async def extract_properties_from_page_id(notion: AsyncClient, page_id: str, property_ids: Union[str, List[str]]) -> Dict[str, List[Any]]:
    """
    단일 page_id에 대해 여러 개의 property를 병렬로 추출하는 함수.
    각 property에 대해 페이지네이션을 통해 모든 데이터를 가져옵니다.
    
    :param notion: Notion 비동기 클라이언트
    :param page_id: Notion 페이지 ID
    :param property_ids: 추출할 property ID 리스트
    :return: 각 속성 ID와 그에 해당하는 데이터의 딕셔너리
    """
    property_ids = [property_ids] if isinstance(property_ids, str) else property_ids

    tasks = [_extract_property_from_page_id(notion, page_id, prop_id) for prop_id in property_ids]
    results = await asyncio.gather(*tasks)

    # 결과를 property_id와 매핑하여 반환
    return {property_id: result for property_id, result in zip(property_ids, results)}

async def _page_id_to_title(notion: AsyncClient, page_id: str) -> str:
    """
    주어진 page_id에 대한 제목을 반환하는 함수.
    페이지네이션을 지원하여 제목이 여러 페이지에 걸쳐 있는 경우 모든 제목을 추출합니다.
    
    :param notion: Notion 비동기 클라이언트
    :param page_id: Notion 페이지 ID
    :return: 페이지 제목 (plain_text)
    """
    titles = []
    has_more = True
    start_cursor = None

    while has_more:
        result = await notion.pages.retrieve(page_id=page_id, start_cursor=start_cursor)
        
        # 제목을 저장
        if 'properties' in result and '이름' in result['properties']:
            titles.extend([item['plain_text'] for item in result['properties']['이름']['title']])
        
        # 다음 페이지가 있는지 확인
        has_more = result.get('has_more', False)
        start_cursor = result.get('next_cursor', None)

    # 모든 제목을 합쳐서 반환
    return ' '.join(titles)

async def page_ids_to_titles(notion: AsyncClient, page_ids: Union[List[str], str]) -> List[str]:
    """
    여러 개의 page_id에 대해 병렬로 제목을 추출하는 함수.
    
    :param notion: Notion 비동기 클라이언트
    :param page_ids: 페이지 ID 리스트
    :return: 제목의 리스트
    """
    page_ids = [page_ids] if isinstance(page_ids, str) else page_ids

    tasks = [_page_id_to_title(notion, page_id) for page_id in page_ids]
    results = await asyncio.gather(*tasks)
    return results

def extract_relation_ids(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[str]:
    """
    주어진 relation property list에서 relation id만 추출하는 함수.
    
    :param data: relation 정보를 담고 있는 리스트
    :return: relation ID만을 담은 리스트
    """
    data = [data] if isinstance(data, dict) else data
    return [item['relation']['id'] for item in data if 'relation' in item and 'id' in item['relation']]

def extract_titles_from_pages(data: Union[Dict[str, Any], List[Dict[str, Any]]], property_name = "이름") -> List[str]:
    """
    주어진 page data list에서 title property 추출하는 함수.
    
    :param data: list of dict or dict (info of pages)
    :return: title만을 담은 리스트
    """
    data = [data] if isinstance(data, dict) else data
    return [item['properties'][property_name]['title'][0]['plain_text'] for item in data]

def extract_ids_from_pages(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[str]:
    """
    주어진 page data list에서 title property 추출하는 함수.
    
    :param data: list of dict or dict (info of pages)
    :return: id만을 담은 리스트
    """
    data = [data] if isinstance(data, dict) else data
    return [item.get("id") for item in data]
    

# res에서 각 property의 relation ID들을 리스트로 변환
def extract_relation_ids_from_response(res: Dict[str, Any]) -> List[List[str]]:
    """
    Notion API response에서 relation ID들을 추출하여 리스트로 반환하는 함수.
    
    :param res: Notion API에서 반환된 response 데이터
    :return: 각 property에 대한 relation ID들을 포함하는 리스트
    """
    return [[item['relation']['id'] for item in items if 'relation' in item] for items in res.values()]
