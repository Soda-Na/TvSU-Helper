from aiogram                    import types
from aiogram.filters.command    import CommandStart

from .                          import dispatcher

@dispatcher.message(CommandStart())
async def start(message: types.Message):
    await message.answer("прив")