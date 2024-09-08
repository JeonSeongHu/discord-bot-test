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

@bot.command(name='help', help='봇에서 사용할 수 있는 명령어 목록을 제공합니다.')
async def help_command(ctx):
    try:
        embed = discord.Embed(title="📚 도움말 | 아래는 사용 가능한 명령어 목록입니다.", description="", color=0x3498db)
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # !내정보 명령어
        embed.add_field(
            name="👤 **!내정보**",
            value="**설명**: Notion 데이터베이스에서 사용자의 정보를 가져옵니다.\n**사용 예시**: `!내정보`",
            inline=False
        )

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # !일정 명령어
        embed.add_field(
            name="🗓️ **!일정**",
            value="**설명**: Notion 일정 데이터베이스에서 특정 조건으로 일정을 검색하고 결과를 표시합니다.\n**사용 예시**:\n- `!일정 name:branch, date:2024-09-09` (특정 이름과 날짜로 검색)\n- `!일정 date:next week` (자연어 날짜 검색 지원)",
            inline=False
        )

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # !멤버 명령어
        embed.add_field(
            name="👥 **!멤버**",
            value="**설명**: Notion 데이터베이스에서 특정 이름 또는 Discord ID로 멤버를 검색합니다.\n**사용 예시**:\n- `!멤버 홍길동` (이름으로 검색)\n- `!멤버 123456789012345678` (Discord ID로 검색)",
            inline=False
        )

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # !공지생성 명령어
        embed.add_field(
            name="📢 **!공지생성**",
            value="**설명**: Notion 일정 페이지를 기반으로 출석 또는 등록 공지를 작성하고, 출석 여부를 확인합니다. 노션 ID는 \"!일정\" 으로 검색하세요.\n\n\"출석\"은 5분이 지나면 자동으로 종료되며, 종료 시 등록자와 출석자를 비교하여 자동으로 출석 체크가 이루어집니다. 출석 체크 결과는 노션에 자동으로 저장되며, 공지 생성자에게도 DM으로 발송됩니다. \n**사용 예시**:\n- `!공지생성 [노션 페이지 ID] 출석 🚀` (출석 공지 작성, 3분간 유지 후 삭제, 커스텀 이모지 사용)\n- `!공지생성 [노션 페이지 ID] 등록 ` (등록 공지 작성 및 기본 이모지 사용, 시간이 지나도 삭제되지 않음.)",
            inline=False
        )

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        embed.set_footer(text="각 명령어의 형식과 사용 방법을 참고하세요. 문제가 있을 경우 관리자에게 문의하세요.")

        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"도움말을 생성하는 동안 오류가 발생했습니다: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)
        pprint(f"Error in help_command: {str(e)}")


# 사용자 자신의 정보를 요청할 때 실행되는 명령어
@bot.command(name='내정보', help='Notion에서 자신의 정보를 가져옵니다.')
async def myinfo(ctx):
    try:
        user_id = ctx.author.id  # Discord 사용자 ID
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
                await ctx.author.send(embed=embed)  # 사용자에게 DM으로 전송
            else:
                embed = discord.Embed(title="오류", description="Notion에서 당신의 정보를 찾을 수 없습니다.", color=0xff0000)
                await ctx.author.send(embed=embed)  # 사용자에게 DM으로 전송

        except Exception as e:
            embed = discord.Embed(title="오류 발생", description=f"Notion API 요청 중 문제가 발생했습니다: {str(e)}", color=0xff0000)
            await ctx.author.send(embed=embed)
            pprint(f"Error in myinfo: {str(e)}")

    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"내정보 명령어 처리 중 오류가 발생했습니다: {str(e)}", color=0xff0000)
        await ctx.author.send(embed=embed)
        pprint(f"Error in myinfo: {str(e)}")


@bot.command(name='일정', help='Notion 일정 데이터베이스에서 특정 조건으로 일정을 검색하고, 장소 및 날짜 등 추가 정보를 제공합니다.')
async def search_schedule(ctx, *, query: str = None):
    if not query:  # query 인자가 제공되지 않으면
        embed = discord.Embed(title="오류", description="일정 검색을 위한 query가 필요합니다. 예시: `!일정 name:회의, date:2024-09-09`", color=0xff0000)
        pprint(f"Error in 검색 조건 오류: 일정 검색을 위한 query가 필요합니다")
        await ctx.send(embed=embed)
        return

    conditions = []
    database_id = NOTION_SCHEDULE_DB_ID

    try:
        # 조건을 쉼표(,)로 구분하여 처리
        queries = query.split(",")  # 여러 조건을 쉼표로 구분

        for q in queries:
            if ":" in q:
                # 조건을 'type: value' 형식으로 구분
                condition_type, condition_value = q.split(":")
                valid_conditions =["date", "name", "tag"] 
                if condition_type not in valid_conditions:
                    embed = discord.Embed(title="검색 조건 오류", description=f"{condition_type}은 유효하지 않은 조건입니다. 조건의 key는 {', '.join(valid_conditions)}만 가능합니다.", color=0xff0000)
                    await ctx.send(embed=embed)
                    pprint(f"Error in 검색 조건 오류: {condition_type}은 유효하지 않은 조건입니다.")
                    return
                conditions.append({condition_type.strip(): condition_value.strip()})
            else:
                embed = discord.Embed(title="오류", description="잘못된 형식입니다. 조건은 'type: value' 형식으로 입력해주세요.", color=0xff0000)
                await ctx.send(embed=embed)
                return

    except ValueError as e:
        embed = discord.Embed(title="쿼리 파싱 오류", description="쿼리를 파싱하는 중 오류가 발생했습니다. 형식이 올바른지 확인해주세요.", color=0xff0000)
        await ctx.send(embed=embed)
        pprint(f"Error in 일정 명령어 쿼리 파싱: {str(e)}")
        return

    try:
        # Notion 클라이언트 생성
        notion_client = AsyncClient(auth=NOTION_API_KEY)
        result = await search_schedules_in_database(notion_client, database_id, conditions)

        # 검색 결과가 있는지 확인
        if not result or not result[0]:
            embed = discord.Embed(title="결과 없음", description="Notion에서 해당 조건으로 예정된 스케줄을 찾을 수 없습니다.", color=0xff0000)
            await ctx.send(embed=embed)
            return

        # 검색 결과가 여러 개일 경우 처리
        if len(result[0]) > 1:
            names = extract_titles_from_pages(result[0])
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
            schedule_info = result[0][0]
            formatted_info = format_notion_schedule_info(schedule_info, prefix="-", return_notion_id=True)
            embed = discord.Embed(title="검색된 정보", description=f"{formatted_info}", color=0x00ff00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="결과 없음", description="Notion에서 해당 조건으로 예정된 스케줄을 찾을 수 없습니다.", color=0xff0000)
            await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"Notion API 요청 중 문제가 발생했습니다. 조건을 다시 확인해주세요.", color=0xff0000)
        await ctx.send(embed=embed)
        pprint(f"Error in 일정 명령어: {str(e)}")


@bot.command(name='멤버', help='Notion에서 특정 이름이나 ID로 멤버를 검색합니다.')
async def search_member(ctx, query: str=None):
    """
    사용자가 제공한 이름 또는 Discord ID로 Notion 데이터베이스에서 멤버를 검색하는 함수.
    
    :param query: 검색할 이름 또는 Discord ID
    """
    if not query:  # query 인자가 제공되지 않으면
        embed = discord.Embed(title="오류", description="멤버 검색을 위한 query가 필요합니다. 예시: `!멤버 변서연`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
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
            member_info = result[0][0]
            formatted_info = format_notion_member_info(member_info, prefix="-")
            
            embed = discord.Embed(title="검색된 정보", description=f"{formatted_info}", color=0x00ff00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="결과 없음", description="Notion에서 해당 조건으로 멤버를 찾을 수 없습니다.", color=0xff0000)
            await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"Notion API 요청 중 문제가 발생했습니다. 조건을 다시 확인해주세요.", color=0xff0000)
        await ctx.send(embed=embed)
        pprint(f"Error in 멤버 명령어: {str(e)}")


@bot.command(name='공지생성', help='노션 일정에 대한 공지를 작성하고 출석/등록을 처리합니다.')
async def create_notice(ctx, notion_page_id: str, notice_type: str, emoji: str = "📢"):
    """
    노션 일정 페이지를 기반으로 출석 또는 등록 공지를 작성하는 함수.
    
    :param notion_page_id: 노션 페이지 ID (행사 정보가 포함된 페이지)
    :param notice_type: '출석' 또는 '등록' 중 하나
    :param emoji: 공지에 사용할 이모지
    :param duration: 초단위로 출석 여부를 확인할 제한 시간 (출석의 경우)
    """

    if notice_type not in ["출석", "등록"]:
        embed = discord.Embed(title="오류", description="공지의 종류는 '등록', '출석' 중 하나여야 합니다. 예시: `!공지생성 [ID] 등록`", color=0xff0000)
        await ctx.send(embed=embed)
    try:
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

        if notice_type == "출석":
            embed.add_field(
                name="생성 5분 후에는 체크해도 출석으로 등록되지 않습니다.",
                value="",
                inline=False
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

        await ctx.message.delete()


        duration = 5

        # 출석 제한 시간이 설정된 경우
        if notice_type == "출석" and duration:
            await asyncio.sleep(duration)
            await ctx.send(f"출석 확인 시간이 종료되었습니다.")
            del attendance_message_store[bot_message.id]

            # 출석 확인 시간이 종료되면 결석자 업데이트 및 DM 전송
            await update_absentees_and_send_dm(notion_client, notion_page_id, ctx.author)

    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"공지 생성 중 오류가 발생했습니다: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)
        pprint(f"Error in 공지생성: {str(e)}")

# 노션 페이지 관계를 업데이트하는 함수
async def update_notion_page_relation(user, notion_client, page_id: str, property_name: str, related_page_id: str):
    """
    노션 페이지의 특정 relation 필드를 업데이트하는 함수.
    
    :param user: 메시지를 보낼 discord user
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
        await user.send(embed=embed)  # 사용자에게 DM으로 전송

    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"노션 페이지 업데이트 중 오류 발생: {str(e)}", color=0xff0000)
        await user.send(embed=embed)
        pprint(f"Error in update_notion_page_relation: {str(e)}")


# 노션 페이지 관계를 제거하는 함수
async def remove_notion_page_relation(user, notion_client, page_id: str, property_name: str, related_page_id: str):
    """
    노션 페이지의 특정 relation 필드에서 관계를 제거하는 함수.

    :param user: 메시지를 보낼 discord user
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
        await user.send(embed=embed)  # 사용자에게 DM으로 전송

    except Exception as e:
        embed = discord.Embed(title="오류 발생", description=f"노션 페이지 관계 제거 중 오류 발생: {str(e)}", color=0xff0000)
        await user.send(embed=embed)
        pprint(f"Error in remove_notion_page_relation: {str(e)}")


# 이모지 추가 시 노션 페이지와 관계를 업데이트하는 이벤트 핸들러
@bot.event
async def on_raw_reaction_add(payload):
    """
    사용자가 특정 메시지에 이모지를 추가할 때 발생하는 이벤트 처리.
    
    :param payload: 이모지 반응 관련 정보
    """
    try:
        if payload.message_id not in attendance_message_store:
            return  # 저장된 출석 또는 등록 메시지가 아닌 경우 처리하지 않음

        user = bot.get_user(payload.user_id)
        if not user:
            return

        notion_client = AsyncClient(auth=NOTION_API_KEY)
        message_data = attendance_message_store[payload.message_id]
        notion_page_id = message_data["notion_page_id"]
        notice_type = message_data["notice_type"]

        # 사용자 정보 찾기
        conditions = [{'discord_id': str(payload.user_id)}]
        result = await search_members_in_database(notion_client, NOTION_MEMBER_DB_ID, conditions)

        if result and len(result[0]) > 0:
            member_info = result[0][0]
            member_page_id = member_info['id']

            # 노션 페이지에 사용자 추가
            property_name = "출석자 (인정 결석 포함)" if notice_type == "출석" else "등록자"
            await update_notion_page_relation(user, notion_client, notion_page_id, property_name, member_page_id)
        else:
            embed = discord.Embed(title="오류", description=f"노션에서 해당 사용자 {payload.user_id}를 찾을 수 없습니다.", color=0xff0000)
            await user.send(embed=embed)

    except Exception as e:
        user = bot.get_user(payload.user_id)
        embed = discord.Embed(title="오류 발생", description=f"이모지 처리 중 오류가 발생했습니다: {str(e)}", color=0xff0000)
        if user:
            await user.send(embed=embed)
        pprint(f"Error in on_raw_reaction_add: {str(e)}")


# 이모지 제거 시 노션 페이지에서 관계를 제거하는 이벤트 핸들러
@bot.event
async def on_raw_reaction_remove(payload):
    """
    사용자가 특정 메시지에서 이모지를 제거할 때 발생하는 이벤트 처리.
    
    :param payload: 이모지 반응 관련 정보
    """
    try:
        if payload.message_id not in attendance_message_store:
            return  # 저장된 출석 또는 등록 메시지가 아닌 경우 처리하지 않음

        user = bot.get_user(payload.user_id)
        if not user:
            return

        notion_client = AsyncClient(auth=NOTION_API_KEY)
        message_data = attendance_message_store[payload.message_id]
        notion_page_id = message_data["notion_page_id"]
        notice_type = message_data["notice_type"]

        # 사용자 정보 찾기
        conditions = [{'discord_id': str(payload.user_id)}]
        result = await search_members_in_database(notion_client, NOTION_MEMBER_DB_ID, conditions)

        if result and len(result[0]) > 0:
            member_info = result[0][0]
            member_page_id = member_info['id']

            # 노션 페이지에서 사용자 제거
            property_name = "출석자 (인정 결석 포함)" if notice_type == "출석" else "등록자"
            await remove_notion_page_relation(user, notion_client, notion_page_id, property_name, member_page_id)
        else:
            embed = discord.Embed(title="오류", description=f"노션에서 해당 사용자 {payload.user_id}를 찾을 수 없습니다.", color=0xff0000)
            await user.send(embed=embed)

    except Exception as e:
        user = bot.get_user(payload.user_id)
        embed = discord.Embed(title="오류 발생", description=f"이모지 제거 처리 중 오류가 발생했습니다: {str(e)}", color=0xff0000)
        if user:
            await user.send(embed=embed)
        pprint(f"Error in on_raw_reaction_remove: {str(e)}")


async def update_absentees_and_send_dm(notion_client, notion_page_id: str, author):
    """
    등록자 목록과 출석자 목록을 비교하여, 등록자는 있지만 출석하지 않은 사람을 결석자 목록에 추가하고,
    공지 생성자에게 등록자, 출석자, 결석자 목록을 DM으로 전송하는 함수.

    :param notion_client: Notion 비동기 API 클라이언트
    :param notion_page_id: 노션 페이지 ID (행사 정보가 포함된 페이지)
    :param author: 공지 생성 명령어를 실행한 사용자 (DM 전송 대상)
    """
    try:
        # 페이지 정보 가져오기
        page_data = await notion_client.pages.retrieve(page_id=notion_page_id)
        
        # 등록자 목록 가져오기
        registrants = page_data['properties'].get('등록자', {}).get('relation', [])
        registrant_ids = [r['id'] for r in registrants]  # 등록자의 노션 페이지 ID 리스트
        registrant_names = await page_ids_to_titles(notion_client, registrant_ids)  # 등록자 이름 가져오기

        # 출석자 목록 가져오기
        attendees = page_data['properties'].get('출석자 (인정 결석 포함)', {}).get('relation', [])
        attendee_ids = [a['id'] for a in attendees]  # 출석자의 노션 페이지 ID 리스트
        attendee_names = await page_ids_to_titles(notion_client, attendee_ids)  # 출석자 이름 가져오기

        # 등록자는 있지만 출석하지 않은 사람 찾기
        absentees_ids = [r_id for r_id in registrant_ids if r_id not in attendee_ids]
        absentee_names = await page_ids_to_titles(notion_client, absentees_ids)  # 결석자 이름 가져오기

        # 결석자 목록에 추가
        if absentees_ids:
            absentees = page_data['properties'].get('결석자', {}).get('relation', [])
            absentee_ids_existing = [a['id'] for a in absentees]  # 기존 결석자의 노션 페이지 ID 리스트

            # 새로운 결석자 추가 (중복되지 않도록 처리)
            new_absentees = [r_id for r_id in absentees_ids if r_id not in absentee_ids_existing]
            
            if new_absentees:
                updated_absentees = absentee_ids_existing + [{"id": absentee_id} for absentee_id in new_absentees]

                # 결석자 목록 업데이트
                await notion_client.pages.update(
                    page_id=notion_page_id,
                    properties={
                        "결석자": {
                            "relation": updated_absentees
                        }
                    }
                )
                print(f"새로운 결석자가 추가되었습니다: {new_absentees}")

        # DM으로 등록자, 출석자, 결석자 목록 전송
        message = (
            f"📋 **출석자 명단**\n{', '.join(attendee_names) if attendee_names else '없음'}\n\n"
            f"📝 **등록자 명단**\n{', '.join(registrant_names) if registrant_names else '없음'}\n\n"
            f"❌ **결석자 명단**\n{', '.join(absentee_names) if absentee_names else '없음'}"
        )
        embed = discord.Embed(title="출석 확인 결과", description=message, color=0x00ff00)
        await author.send(embed=embed)

    except Exception as e:
        print(f"결석자 목록 업데이트 및 DM 전송 중 오류 발생: {str(e)}")
        await author.send(f"결석자 목록 업데이트 중 오류 발생: {str(e)}")

# 봇 실행
bot.run(DISCORD_TOKEN)
