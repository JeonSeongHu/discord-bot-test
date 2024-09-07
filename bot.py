# bot.py
import os
import discord
from dotenv import load_dotenv

# 환경 변수를 .env 파일에서 로딩
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(command_prefix='!', intents=intents)

@client.event
async def on_ready():
  print(f'We have logged in as {client.user.name}')

# start the bot
client.run(TOKEN)