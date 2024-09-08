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

# 봇 실행
bot.run(DISCORD_TOKEN)