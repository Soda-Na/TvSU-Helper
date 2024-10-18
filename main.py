import asyncio
import os

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties

dispatcher = Dispatcher()

bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))

async def main():
    dispatcher.startup.register(lambda: print("Bot started"))
    await dispatcher.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
