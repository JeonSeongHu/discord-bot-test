import os, json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from notion_client import Client, AsyncClient

from utils.notion import search_members_in_database, format_notion_member_info
from utils.notion import search_schedules_in_database, format_notion_schedule_info
from utils.notion import extract_titles_from_pages, page_ids_to_titles
from pprint import pprint

import json

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 Discord와 Notion API 키를 가져오기
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_MEMBER_DB_ID = os.getenv("NOTION_MEMBER_DB_ID")
NOTION_SCHEDULE_DB_ID = os.getenv("NOTION_SCHEDULE_DB_ID")


# Notion API 클라이언트 초기화
notion = Client(auth=NOTION_API_KEY)

# Discord 봇 명령어 프리픽스 설정
intents = discord.Intents.default()
intents.members = True  # 서버 멤버 정보를 가져오려면 이 권한이 필요합니다
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 봇이 시작될 때 실행되는 이벤트
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

# 사용자 자신의 정보를 요청할 때 실행되는 명령어
@bot.command(name='myinfo', help='Notion에서 자신의 정보를 가져옵니다.')
async def myinfo(ctx):
    # 사용자 정보 가져오기
    user_id = ctx.author.id  # Discord 사용자 ID
    
    # Notion에서 해당 사용자의 정보를 검색
    conditions = [{'discord_id': user_id}]
    database_id = NOTION_MEMBER_DB_ID

    # 검색 결과 가져오기 (Notion에서 사용자 정보 검색)
    try:
        notion_client = AsyncClient(auth=NOTION_API_KEY)
        result = await search_members_in_database(notion_client, database_id, conditions)
        
        # 검색된 결과 출력
        if result and len(result) > 0:
            member_info = result[0][0]
            formatted_info = format_notion_member_info(member_info, prefix="-")  # 결과 포맷팅
            await ctx.send(f"당신의 정보는 다음과 같습니다:\n {formatted_info}")
        else:
            await ctx.send("Notion에서 당신의 정보를 찾을 수 없습니다.")

    except Exception as e:
        await ctx.send(f"오류가 발생했습니다: {str(e)}")


@bot.command(name='일정', help='Notion에서 특정 이름이나 태그로 스케줄을 검색합니다.')
async def 일정(ctx, *, query: str):
    """
    사용자가 제공한 여러 조건을 Notion 데이터베이스에서 스케줄을 검색하는 함수.
    
    :param query: 검색할 조건들 (name:fetch, date:this week 형식으로 입력 가능)
    """

    conditions = []
    database_id = NOTION_SCHEDULE_DB_ID

    # 조건을 쉼표(,)로 구분하여 처리
    queries = query.split(",")  # 여러 조건을 쉼표로 구분

    for q in queries:
        if ":" in q:
            # 조건을 'type: value' 형식으로 구분
            condition_type, condition_value = q.split(":")
            conditions.append({condition_type.strip(): condition_value.strip()})
        else:
            await ctx.send(f"잘못된 형식입니다. 조건은 'type: value' 형식으로 입력해주세요.")
            return

    # Notion 클라이언트 생성
    notion_client = AsyncClient(auth=NOTION_API_KEY)

    # 검색 조건을 전달하여 데이터베이스 검색
    result = await search_schedules_in_database(notion_client, database_id, conditions)
    
    # 검색 결과가 여러 개일 경우 처리
    if result and len(result[0]) > 1:
        # 결과가 2개 이상이면 이름만 출력하여 선택을 요청
        # pprint(result)
        names = extract_titles_from_pages(result[0])
        name_list = '\n'.join([f"{i+1}. {name}" for i, name in enumerate(names)])
        
        await ctx.send(f"다음과 같은 검색 결과가 있습니다. 번호를 선택해주세요:\n{name_list}")

        def check(m):
            return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= len(names)
        
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            selected_index = int(msg.content) - 1
            selected_schedule = result[0][selected_index]
            formatted_info = format_notion_schedule_info(selected_schedule, prefix="-")
            await ctx.send(f"선택된 정보:\n{formatted_info}")
        except asyncio.TimeoutError:
            await ctx.send("시간이 초과되었습니다. 다시 시도해주세요.")
    elif result and len(result[0]) == 1:
        # 결과가 하나만 있을 경우 바로 정보 출력
        schedule_info = result[0][0]
        formatted_info = format_notion_schedule_info(schedule_info, prefix="-")
        await ctx.send(f"검색된 정보:\n{formatted_info}")
    else:
        # 결과가 없을 경우
        await ctx.send("Notion에서 해당 조건으로 예정된 스케줄을 찾을 수 없습니다.")



@bot.command(name='멤버', help='Notion에서 특정 이름이나 ID로 멤버를 검색합니다.')
async def 멤버(ctx, *, query: str):
    """
    사용자가 제공한 이름 또는 Discord ID로 Notion 데이터베이스에서 멤버를 검색하는 함수.
    
    :param query: 검색할 이름 또는 Discord ID
    """
    # Discord ID인지 이름인지 구분
    try:
        # ID가 숫자이면 ID로 검색
        discord_id = int(query)
        conditions = [{'discord_id': discord_id}]
    except ValueError:
        # ID가 아니면 이름으로 검색
        name = query
        conditions = [{'name': name}]
    
    database_id = NOTION_MEMBER_DB_ID

    # 검색 결과 가져오기
    notion_client = AsyncClient(auth=NOTION_API_KEY)
    result = await search_members_in_database(notion_client, database_id, conditions)
    
    # 검색 결과가 여러 개일 경우 처리
    if result and len(result[0]) > 1:
        # 결과가 2개 이상이면 이름만 출력하여 선택을 요청
        names = extract_titles_from_pages(result[0])
        name_list = '\n'.join([f"{i+1}. {name}" for i, name in enumerate(names)])
        
        await ctx.send(f"다음과 같은 검색 결과가 있습니다. 번호를 선택해주세요:\n{name_list}")

        def check(m):
            return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= len(names)
        
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            selected_index = int(msg.content) - 1
            selected_member = result[0][selected_index]
            formatted_info = format_notion_member_info(selected_member, prefix="-")
            await ctx.send(f"선택된 정보:\n{formatted_info}")
        except asyncio.TimeoutError:
            await ctx.send("시간이 초과되었습니다. 다시 시도해주세요.")
    elif result and len(result[0]) == 1:
        # 결과가 하나만 있을 경우 바로 정보 출력
        member_info = result[0][0]
        formatted_info = format_notion_member_info(member_info, prefix="-")
        await ctx.send(f"검색된 정보:\n{formatted_info}")
    else:
        # 결과가 없을 경우
        await ctx.send("Notion에서 해당 조건으로 멤버를 찾을 수 없습니다.")

# 메시지 ID와 JSON 데이터를 저장하는 메모리 내 저장소
message_data_store = {}

@bot.command(name='create_message', help='노션 페이지와 이모지-property 매핑 정보를 포함하여 봇이 메시지를 작성합니다.')
async def create_message(ctx, notion_page_id: str, *, emoji_property_map: str):
    """
    노션 페이지 ID와 여러 이모지-property 매핑 정보를 받아 메시지를 작성합니다.
    
    :param notion_page_id: 노션 페이지 ID
    :param emoji_property_map: 이모지와 property name을 매핑하는 정보 (예: 😃:relation_property1, 😢relation_property2)
    """
    # Notion API를 통해 페이지 제목 가져오기
    notion_client = AsyncClient(auth=NOTION_API_KEY)
    notion_page_title = await page_ids_to_titles(notion_client, notion_page_id)
    notion_page_title = notion_page_title[0]

    # emoji_property_map을 dict로 변환
    emoji_property_dict = {}
    try:
        pairs = emoji_property_map.split(", ")
        for pair in pairs:
            emoji, property_name = pair.split(":")
            emoji_property_dict[emoji.strip()] = property_name.strip()
    except ValueError:
        await ctx.send("잘못된 형식의 이모지-property 매핑 정보입니다. 올바른 형식은 😃:property1, 😢:property2 입니다.")
        return

    # 메시지 작성
    bot_message = await ctx.send(f"이 메시지에 반응하면 {notion_page_title}이 업데이트됩니다.")

    # 이모지 추가
    for emoji in emoji_property_dict.keys():
        await bot_message.add_reaction(emoji)

    # 메시지 ID와 매핑 정보 저장
    message_data_store[bot_message.id] = {
        "notion_page_id": notion_page_id,
        "emoji_property_map": emoji_property_dict
    }

    await ctx.send(f"메시지가 작성되었고, 노션 페이지 {notion_page_title}와 이모지가 매핑되었습니다.")


@bot.event
async def on_raw_reaction_add(payload):
    """
    사용자가 특정 메시지에 이모지를 추가할 때 발생하는 이벤트 처리.
    
    :param payload: 이모지 반응 관련 정보
    """
    await handle_reaction_change(payload, action="add")


@bot.event
async def on_raw_reaction_remove(payload):
    """
    사용자가 특정 메시지에서 이모지를 제거할 때 발생하는 이벤트 처리.
    
    :param payload: 이모지 반응 관련 정보
    """
    await handle_reaction_change(payload, action="remove")


async def handle_reaction_change(payload, action: str):
    """
    이모지 반응이 추가되거나 제거될 때 노션 페이지를 업데이트하는 함수.
    
    :param payload: 이모지 반응 관련 정보
    :param action: 'add' 또는 'remove'를 지정하여 이모지 추가 또는 제거 여부 확인
    """
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    message = await channel.fetch_message(payload.message_id)

    # 메시지 ID를 기준으로 매핑 정보 조회
    if message.id not in message_data_store:
        return

    data = message_data_store[message.id]
    notion_page_id = data["notion_page_id"]
    emoji_property_dict = data["emoji_property_map"]

    emoji_str = str(payload.emoji)

    # 반응된 이모지가 매핑된 이모지인지 확인
    if emoji_str in emoji_property_dict:
        user_id = payload.user_id

        # 노션 클라이언트 초기화
        notion_client = AsyncClient(auth=NOTION_API_KEY)

        # 노션 멤버 명부에서 해당 사용자 ID 찾기
        conditions = [{'discord_id': str(user_id)}]
        result = await search_members_in_database(notion_client, NOTION_MEMBER_DB_ID, conditions)
        
        if result and len(result[0]) > 0:
            # 멤버 정보를 찾으면 관련 페이지의 특정 property에 relation 값 추가 또는 제거
            member_info = result[0][0]
            member_page_id = member_info['id']
            property_name = emoji_property_dict[emoji_str]

            if action == "add":
                await update_notion_page_relation(notion_client, notion_page_id, property_name, member_page_id)
                await channel.send(f"사용자 {user_id}가 메시지 {message.id}에 {payload.emoji} 이모지를 추가하여 노션 페이지가 업데이트되었습니다.")
            elif action == "remove":
                await remove_notion_page_relation(notion_client, notion_page_id, property_name, member_page_id)
                await channel.send(f"사용자 {user_id}가 메시지 {message.id}에서 {payload.emoji} 이모지를 제거하여 노션 페이지가 업데이트되었습니다.")
        else:
            await channel.send(f"노션에서 해당 사용자 {user_id}를 찾을 수 없습니다.")


# 노션 페이지 관계를 추가하는 함수
async def update_notion_page_relation(notion_client, page_id: str, property_name: str, related_page_id: str):
    """
    노션 페이지의 특정 relation 필드를 업데이트하는 함수.
    
    :param notion_client: Notion 비동기 API 클라이언트
    :param page_id: 노션 페이지 ID
    :param property_name: 업데이트할 프로퍼티 이름
    :param related_page_id: relation으로 추가할 페이지 ID
    """
    try:
        await notion_client.pages.update(
            page_id=page_id,
            properties={
                property_name: {
                    "relation": [{"id": related_page_id}]
                }
            }
        )
        print(f"페이지 {page_id}의 {property_name}이 업데이트되었습니다.")
    except Exception as e:
        print(f"노션 페이지 업데이트 중 오류 발생: {e}")


# 노션 페이지 관계를 제거하는 함수 (프로토타입)
async def remove_notion_page_relation(notion_client, page_id: str, property_name: str, related_page_id: str):
    """
    노션 페이지의 특정 relation 필드에서 관계를 제거하는 함수.
    
    :param notion_client: Notion 비동기 API 클라이언트
    :param page_id: 노션 페이지 ID
    :param property_name: 업데이트할 프로퍼티 이름
    :param related_page_id: relation에서 제거할 페이지 ID
    """
    try:
        # 기존 관계를 가져옴
        page_data = await notion_client.pages.retrieve(page_id=page_id)
        relations = page_data['properties'][property_name]['relation']
        
        # 제거할 관계 필터링
        updated_relations = [r for r in relations if r['id'] != related_page_id]
        
        # 관계 업데이트
        await notion_client.pages.update(
            page_id=page_id,
            properties={
                property_name: {
                    "relation": updated_relations
                }
            }
        )
        print(f"페이지 {page_id}의 {property_name}에서 관계가 제거되었습니다.")
    except Exception as e:
        print(f"노션 페이지 관계 제거 중 오류 발생: {e}")

# 봇 실행
bot.run(DISCORD_TOKEN)