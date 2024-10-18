import asyncio

from aiogram                        import Dispatcher

dispatcher = Dispatcher(name="main")


async def main():
    await dispatcher.startup.register(lambda router: print(f"Router {router} started"))
    await dispatcher.start_polling(main_bot)

if __name__ == '__main__':
    asyncio.run(main())
