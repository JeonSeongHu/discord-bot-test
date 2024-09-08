import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from notion_client import Client, AsyncClient

from utils.notion import search_members_in_database, format_notion_member_info

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 Discord와 Notion API 키를 가져오기
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_MEMBER_DB_ID = os.getenv("NOTION_MEMBER_DB_ID")

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


@bot.command(name='searchinfo', help='Notion에서 특정 이름이나 ID로 멤버를 검색합니다.')
async def searchinfo(ctx, *, query: str):
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
        names = [member['properties']['이름']['title'][0]['plain_text'] for member in result[0]]
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

# 봇 실행
bot.run(DISCORD_TOKEN)