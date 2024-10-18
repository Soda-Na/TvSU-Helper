from aiogram import Router

from .handlers import dispatcher as menu_dispatcher

dispatcher = Router()
dispatcher.include_router(menu_dispatcher)