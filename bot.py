import os, json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from notion_client import Client, AsyncClient

from utils.notion import search_members_in_database, format_notion_member_info
from utils.notion import search_schedules_in_database, format_notion_schedule_info
from utils.notion import extract_titles_from_pages, page_ids_to_titles, safe_extract
from pprint import pprint

import json, asyncio

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 Discord와 Notion API 키를 가져오기
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_MEMBER_DB_ID = os.getenv("NOTION_MEMBER_DB_ID")
NOTION_SCHEDULE_DB_ID = os.getenv("NOTION_SCHEDULE_DB_ID")

attendance_message_store = dict()
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

bot.remove_command('help')

bot.remove_command('help')

@bot.command(name='help', help='봇에서 사용할 수 있는 명령어 목록을 제공합니다.')
async def help_command(ctx):
    embed = discord.Embed(title="📚 도움말 | 아래는 사용 가능한 명령어 목록입니다.", description="", color=0x3498db)
    
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    # !내정보 명령어
    embed.add_field(
        name="👤 **!내정보**",
        value="""
        **설명**: Notion 데이터베이스에서 사용자의 정보를 가져옵니다.
        **사용 예시**: `!내정보`
        """,
        inline=False
    )

    # 빈 필드를 추가하여 여백을 만듦
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    # !일정 명령어
    embed.add_field(
        name="🗓️ **!일정**",
        value="""
        **설명**: Notion 일정 데이터베이스에서 특정 조건으로 일정을 검색하고 결과를 표시합니다.
        **사용 예시**:\n- `!일정 name:branch, date:2024-09-09` (특정 이름과 날짜로 검색)\n- `!일정 location:우정정보관` (장소 기준으로 검색)
        """,
        inline=False
    )

    # 빈 필드를 추가하여 여백을 만듦
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    # !멤버 명령어
    embed.add_field(
        name="👥 **!멤버**",
        value="""
        **설명**: Notion 데이터베이스에서 특정 이름 또는 Discord ID로 멤버를 검색합니다.
        **사용 예시**:\n- `!멤버 홍길동` (이름으로 검색)\n- `!멤버 123456789012345678` (Discord ID로 검색)
        """,
        inline=False
    )

    # 빈 필드를 추가하여 여백을 만듦
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    # !공지생성 명령어
    embed.add_field(
        name="📢 **!공지생성**",
        value="""
        **설명**: Notion 일정 페이지를 기반으로 출석 또는 등록 공지를 작성하고, 출석 여부를 확인합니다. 노션 ID는 "!일정" 으로 검색하세요.
        **사용 예시**:\n- `!공지생성 [노션 페이지 ID] 출석 🚀 60` (출석 공지 작성, 60초간 메세지, 커스텀 이모지 사용)\n- `!공지생성 [노션 페이지 ID] 등록 ` (등록 공지 작성 및 기본 이모지 사용, 등록은 시간 설정 불가)
        """,
        inline=False
    )

    embed.add_field(name="\u200b", value="\u200b", inline=False)

    # 푸터와 썸네일 추가
    embed.set_footer(text="각 명령어의 형식과 사용 방법을 참고하세요. 문제가 있을 경우 관리자에게 문의하세요.")
    embed.set_thumbnail(url="https://example.com/help_icon.png")  # 썸네일 추가

    await ctx.send(embed=embed)


# 사용자 자신의 정보를 요청할 때 실행되는 명령어
@bot.command(name='내정보', help='Notion에서 자신의 정보를 가져옵니다.')
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
            
            # Embed 메시지 생성
            embed = discord.Embed(title="당신의 정보", description=f"{formatted_info}", color=0x00ff00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="오류", description="Notion에서 당신의 정보를 찾을 수 없습니다.", color=0xff0000)
            await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"{str(e)}", color=0xff0000)
        await ctx.send(embed=embed)


@bot.command(name='일정', help='Notion 일정 데이터베이스에서 특정 조건으로 일정을 검색하고, 장소 및 날짜 등 추가 정보를 제공합니다.')
async def 일정(ctx, *, query: str):
    """
    사용자가 입력한 조건을 기반으로 Notion 일정 데이터베이스에서 일정을 검색하는 함수.
    여러 조건을 쉼표로 구분하여 입력할 수 있으며, 각 조건은 'type:value' 형식으로 입력해야 합니다.

    예시:
    !일정 name:fetch, date:this week

    조건:
    - name: 일정의 이름
    - date: 일정 날짜 (this week, next week 등)
    - location: 일정 장소

    검색된 일정은 이름, 장소, 날짜 등의 정보가 표 형식으로 제공되며, 여러 결과가 있을 경우 선택할 수 있습니다.
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
            embed = discord.Embed(title="오류", description="잘못된 형식입니다. 조건은 'type: value' 형식으로 입력해주세요.", color=0xff0000)
            await ctx.send(embed=embed)
            return

    # Notion 클라이언트 생성
    notion_client = AsyncClient(auth=NOTION_API_KEY)

    try:
        # 검색 조건을 전달하여 데이터베이스 검색
        result = await search_schedules_in_database(notion_client, database_id, conditions)

        # 검색 결과가 있는지 확인
        if not result or not result[0]:
            embed = discord.Embed(title="결과 없음", description="Notion에서 해당 조건으로 예정된 스케줄을 찾을 수 없습니다.", color=0xff0000)
            await ctx.send(embed=embed)
            return

        # 검색 결과가 여러 개일 경우 처리
        if len(result[0]) > 1:
            # 여러 결과가 있을 경우 이름, 장소, 날짜 정보를 표 형식으로 출력
            names = extract_titles_from_pages(result[0])
            
            # 장소와 날짜가 없을 때 N/A로 처리
            locations = [schedule.get("properties", {}).get("장소", {}).get("rich_text", [{}])[0].get("plain_text", "N/A")
                         if schedule.get("properties", {}).get("장소", {}).get("rich_text") else "N/A"
                         for schedule in result[0]]
            
            dates = [schedule.get("properties", {}).get("날짜", {}).get("date", {}).get("start", "N/A")
                     if schedule.get("properties", {}).get("날짜", {}).get("date") else "N/A"
                     for schedule in result[0]]

            # 표 형식으로 출력
            embed = discord.Embed(
                title="검색 결과", 
                description="다음과 같은 검색 결과가 있습니다. 번호를 선택해주세요.", 
                color=0x00ff00
            )

            # 검색 결과 추가
            for i, (name, location, date) in enumerate(zip(names, locations, dates)):
                embed.add_field(
                    name=f"{i+1}. {name}", 
                    value=f"**장소**: {location}\n**날짜**: {date}", 
                    inline=False
                )

            await ctx.send(embed=embed)

            def check(m):
                return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= len(names)

            try:
                msg = await bot.wait_for('message', timeout=30.0, check=check)
                selected_index = int(msg.content) - 1
                selected_schedule = result[0][selected_index]
                formatted_info = format_notion_schedule_info(selected_schedule, prefix="-", return_notion_id=True)
                
                embed = discord.Embed(title="선택된 정보", description=f"{formatted_info}", color=0x00ff00)
                await ctx.send(embed=embed)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="시간 초과", description="시간이 초과되었습니다. 다시 시도해주세요.", color=0xff0000)
                await ctx.send(embed=embed)

        elif len(result[0]) == 1:
            # 결과가 하나만 있을 경우 바로 정보 출력
            schedule_info = result[0][0]
            formatted_info = format_notion_schedule_info(schedule_info, prefix="-", return_notion_id=True)
            embed = discord.Embed(title="검색된 정보", description=f"{formatted_info}", color=0x00ff00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="결과 없음", description="Notion에서 해당 조건으로 예정된 스케줄을 찾을 수 없습니다.", color=0xff0000)
            await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"{str(e)}", color=0xff0000)
        await ctx.send(embed=embed)


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
        
        roles = [', '.join([tag.get("name", "") for tag in person.get("properties", {}).get("활동 분야", {}).get("multi_select", [])])
                        if person.get("properties", {}).get("활동 분야", {}).get("multi_select", []) else "N/A"
                        for person in result[0]]
    
        
        embed = discord.Embed(title="검색 결과", description=f"다음과 같은 검색 결과가 있습니다. 번호를 선택해주세요:", color=0x00ff00)
        
        for i, (name, role) in enumerate(zip(names, roles)):
                embed.add_field(
                    name=f"{i+1}. {name}", 
                    value=f"**분야**: {role}", 
                    inline=False
                )

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= len(names)
        
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            selected_index = int(msg.content) - 1
            selected_member = result[0][selected_index]
            formatted_info = format_notion_member_info(selected_member, prefix="-")
            
            embed = discord.Embed(title="선택된 정보", description=f"{formatted_info}", color=0x00ff00)
            await ctx.send(embed=embed)
        except asyncio.TimeoutError:
            embed = discord.Embed(title="시간 초과", description="시간이 초과되었습니다. 다시 시도해주세요.", color=0xff0000)
            await ctx.send(embed=embed)
    elif result and len(result[0]) == 1:
        # 결과가 하나만 있을 경우 바로 정보 출력
        member_info = result[0][0]
        formatted_info = format_notion_member_info(member_info, prefix="-")
        
        embed = discord.Embed(title="검색된 정보", description=f"{formatted_info}", color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="결과 없음", description="Notion에서 해당 조건으로 멤버를 찾을 수 없습니다.", color=0xff0000)
        await ctx.send(embed=embed)


@bot.command(name='공지생성', help='노션 일정에 대한 공지를 작성하고 출석/등록을 처리합니다.')
async def 공지생성(ctx, notion_page_id: str, notice_type: str, emoji: str = "📢", duration: int = None):
    """
    노션 일정 페이지를 기반으로 출석 또는 등록 공지를 작성하는 함수.
    
    :param notion_page_id: 노션 페이지 ID (행사 정보가 포함된 페이지)
    :param notice_type: '출석' 또는 '등록' 중 하나
    :param emoji: 공지에 사용할 이모지
    :param duration: 초단위로 출석 여부를 확인할 제한 시간 (출석의 경우)
    """
    # Notion API를 통해 페이지 정보 가져오기
    notion_client = AsyncClient(auth=NOTION_API_KEY)
    schedule_info = await notion_client.pages.retrieve(page_id=notion_page_id)

    # 일정 정보를 formatting
    formatted_info = format_notion_schedule_info(schedule_info, return_notion_id=False)
    schedule_name = extract_titles_from_pages(schedule_info)[0]

    # 제목에 따라 이모지 변경
    if "branch" in schedule_name:
        emoji = "🌳"
    elif "fetch" in schedule_name:
        emoji = "🚀"

    # 공지 형식으로 메시지 작성
    embed = discord.Embed(
        title=f"{emoji} **{schedule_name} {notice_type} 공지**", 
        description=f"이 메시지에 체크하여 {emoji} {schedule_name}에 {notice_type}해주세요!\n{formatted_info}",
        color=0x00ff00
    )
    bot_message = await ctx.send(embed=embed)
    
    # 이모지 추가 (체크마크)
    await bot_message.add_reaction("✅")

    # 출석 또는 등록에 대한 처리
    attendance_message_store[bot_message.id] = {
        "notion_page_id": notion_page_id,
        "notice_type": notice_type,
        "emoji": "✅"
    }

    # 출석 제한 시간이 설정된 경우
    if notice_type == "출석" and duration:
        await ctx.send(f"출석 확인 제한 시간: {duration}초")
        await asyncio.sleep(duration)
        await ctx.send(f"출석 확인 시간이 종료되었습니다.")
        del attendance_message_store[bot_message.id]


@bot.event
async def on_raw_reaction_add(payload):
    """
    사용자가 특정 메시지에 이모지를 추가할 때 발생하는 이벤트 처리.
    
    :param payload: 이모지 반응 관련 정보
    """
    if payload.message_id not in attendance_message_store:
        return  # 저장된 출석 또는 등록 메시지가 아닌 경우 처리하지 않음

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    message = await channel.fetch_message(payload.message_id)
    notion_page_id = attendance_message_store[message.id]["notion_page_id"]
    notice_type = attendance_message_store[message.id]["notice_type"]
    emoji_str = str(payload.emoji)

    if emoji_str != "✅":  # 체크 이모지 반응만 처리
        return

    user_id = payload.user_id

    # 노션 클라이언트 초기화
    notion_client = AsyncClient(auth=NOTION_API_KEY)

    # 노션 멤버 명부에서 해당 사용자 ID 찾기
    conditions = [{'discord_id': str(user_id)}]
    result = await search_members_in_database(notion_client, NOTION_MEMBER_DB_ID, conditions)

    if result and len(result[0]) > 0:
        member_info = result[0][0]
        member_page_id = member_info['id']

        # 출석 또는 등록 처리
        property_name = "출석자 (인정 결석 포함)" if notice_type == "출석" else "등록자"

        # 노션 페이지에 관계 추가
        await update_notion_page_relation(channel, notion_client, notion_page_id, property_name, member_page_id)
    else:
        embed = discord.Embed(title="오류", description=f"노션에서 해당 사용자 {user_id}를 찾을 수 없습니다.", color=0xff0000)
        await channel.send(embed=embed)


@bot.event
async def on_raw_reaction_remove(payload):
    """
    사용자가 특정 메시지에서 이모지를 제거할 때 발생하는 이벤트 처리.
    
    :param payload: 이모지 반응 관련 정보
    """
    if payload.message_id not in attendance_message_store:
        return  # 저장된 출석 또는 등록 메시지가 아닌 경우 처리하지 않음

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    message = await channel.fetch_message(payload.message_id)
    notion_page_id = attendance_message_store[message.id]["notion_page_id"]
    notice_type = attendance_message_store[message.id]["notice_type"]
    emoji_str = str(payload.emoji)

    if emoji_str != "✅":  # 체크 이모지 반응만 처리
        return

    user_id = payload.user_id

    # 노션 클라이언트 초기화
    notion_client = AsyncClient(auth=NOTION_API_KEY)

    # 노션 멤버 명부에서 해당 사용자 ID 찾기
    conditions = [{'discord_id': str(user_id)}]
    result = await search_members_in_database(notion_client, NOTION_MEMBER_DB_ID, conditions)

    if result and len(result[0]) > 0:
        member_info = result[0][0]
        member_page_id = member_info['id']

        # 출석 또는 등록 취소 처리
        property_name = "출석자 (인정 결석 포함)" if notice_type == "출석" else "등록자"

        # 노션 페이지에서 관계 제거
        await remove_notion_page_relation(channel, notion_client, notion_page_id, property_name, member_page_id)
    else:
        embed = discord.Embed(title="오류", description=f"노션에서 해당 사용자 {user_id}를 찾을 수 없습니다.", color=0xff0000)
        await channel.send(embed=embed)


# 노션 페이지 관계를 업데이트하는 함수
async def update_notion_page_relation(channel, notion_client, page_id: str, property_name: str, related_page_id: str):
    """
    노션 페이지의 특정 relation 필드를 업데이트하는 함수.
    
    :param channel: 메시지를 보낼 discord channel
    :param notion_client: Notion 비동기 API 클라이언트
    :param page_id: 노션 페이지 ID
    :param property_name: 업데이트할 프로퍼티 이름 (출석자 또는 등록자)
    :param related_page_id: relation으로 추가할 페이지 ID
    """
    try:
         # 기존 관계 가져오기
        page_data = await notion_client.pages.retrieve(page_id=page_id)
        existing_relations = page_data['properties'][property_name]['relation']
        
        # 기존 관계에 새로운 관계 추가 (중복되지 않도록 확인)
        if not any(relation['id'] == related_page_id for relation in existing_relations):
            updated_relations = existing_relations + [{"id": related_page_id}]
        else:
            updated_relations = existing_relations
        
        await notion_client.pages.update(
            page_id=page_id,
            properties={
                property_name: {
                    "relation": [{"id": related_page_id}]
                }
            }
        )
        schedule_name, member_name = await page_ids_to_titles(notion_client, [page_id, related_page_id])
        embed = discord.Embed(title="업데이트 완료", description=f"페이지 {schedule_name}의 '{property_name}'에 '{member_name}'가 추가되었습니다.", color=0x00ff00)
        await channel.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"노션 페이지 업데이트 중 오류 발생: {e}", color=0xff0000)
        await channel.send(embed=embed)


# 노션 페이지 관계를 제거하는 함수
async def remove_notion_page_relation(channel, notion_client, page_id: str, property_name: str, related_page_id: str):
    """
    노션 페이지의 특정 relation 필드에서 관계를 제거하는 함수.

    :param channel: 메시지를 보낼 discord channel
    :param notion_client: Notion 비동기 API 클라이언트
    :param page_id: 노션 페이지 ID
    :param property_name: 업데이트할 프로퍼티 이름 (출석자 또는 등록자)
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
        schedule_name, member_name = await page_ids_to_titles(notion_client, [page_id, related_page_id])

        embed = discord.Embed(title="관계 제거 완료", description=f"페이지 {schedule_name}의 '{property_name}'에 '{member_name}'가 제거되었습니다.", color=0x00ff00)
        await channel.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"노션 페이지 관계 제거 중 오류 발생: {e}", color=0xff0000)
        await channel.send(embed=embed)


# 봇 실행
bot.run(DISCORD_TOKEN)
