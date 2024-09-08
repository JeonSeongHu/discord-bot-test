import asyncio
from notion_client import AsyncClient  # 비동기 클라이언트 사용
from dotenv import load_dotenv
from pprint import pprint
import os, sys
from enum import Enum
from typing import List, Dict, Any, Union, Optional

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from utils.condition import Condition
from utils.notion import search_schedules_in_database, page_ids_to_titles, extract_property_from_page_id, extract_relation_ids


async def main():
    notion = AsyncClient(auth=NOTION_API_KEY)

    res = await page_ids_to_titles(notion, page_ids="14be0c6a-78da-4a46-a839-9902a4170c22")
    prop = await extract_property_from_page_id(notion, page_id="14be0c6a-78da-4a46-a839-9902a4170c22", property_id="NNKg")
    pprint(res)
    ids =  extract_relation_ids(prop)
    titles = await page_ids_to_titles(notion, ids)
    print(titles)
    
    # # 검색할 조건들 (리스트 형식으로 여러 조건)
    # conditions_list = [
    #     {'name': "fetch", 'date': 'after 24.09.08'},
    #     {'name': "fetch", 'date': 'before 24.09.12'},
    # ]

    # # 데이터베이스 ID
    # database_id = NOTION_SCHEDULE_DB_ID

    # # 멤버 검색 함수 호출
    # results = await search_schedules_in_database(notion, database_id, conditions_list)
    
    # # 결과 출력
    # for i, result in enumerate(results):
    #     print(f"검색 조건 {i+1}에 대한 결과: {len(result)}개의 행사")
    #     for k in result:
    #         print(k["properties"]["이름"]['title'][0]['plain_text'], k["properties"]["날짜"]["date"]["start"])
    

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve values from environment variables
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_MEMBER_DB_ID = os.getenv("NOTION_MEMBER_DB_ID")
    NOTION_SCHEDULE_DB_ID = os.getenv("NOTION_SCHEDULE_DB_ID")  

    # 비동기 실행
    asyncio.run(main())