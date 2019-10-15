from aiogram import Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from app.middlewares.acl import ACLMiddleware


def setup(dispatcher: Dispatcher):
    from app.middlewares.db import SQLAlchemySessionMiddleware
    from app.misc import i18n

    dispatcher.middleware.setup(LoggingMiddleware("bot"))
    dispatcher.middleware.setup(SQLAlchemySessionMiddleware())
    dispatcher.middleware.setup(ACLMiddleware())
    dispatcher.middleware.setup(i18n)
