import asyncio
import random
from contextlib import suppress

from aiogram import types
from aiogram.dispatcher.handler import SkipHandler
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageToDeleteNotFound
from loguru import logger

from app import config
from app.misc import dp, i18n
from app.services.join_list import join_list

_ = i18n.gettext

cb_join_list = CallbackData("join_chat", "answer")


@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(message: types.Message):
    if message.from_user not in message.new_chat_members:
        logger.opt(lazy=True).info(
            "User {user} add new members to chat {chat}: {new_members}",
            user=lambda: message.from_user.id,
            chat=lambda: message.chat.id,
            new_members=lambda: ", ".join([str(u.id) for u in message.new_chat_members]),
        )
        # TODO: Validate is admin add new members
    else:
        logger.opt(lazy=True).info(
            "New chat members in chat {chat}: {new_members}",
            chat=lambda: message.chat.id,
            new_members=lambda: ", ".join([str(u.id) for u in message.new_chat_members]),
        )

    users = {}
    for new_member in message.new_chat_members:
        await message.chat.restrict(
            new_member.id, permissions=types.ChatPermissions(can_send_messages=False)
        )
        users[new_member.id] = new_member.get_mention()

    buttons = [
        types.InlineKeyboardButton(_("I'm human"), callback_data=cb_join_list.new(answer="human")),
        types.InlineKeyboardButton(_("I'm bot"), callback_data=cb_join_list.new(answer="bot")),
        types.InlineKeyboardButton(_("I'm pet"), callback_data=cb_join_list.new(answer="pet")),
    ]
    random.shuffle(buttons)
    msg = await message.reply(
        _(
            "Welcome {users} in this chat.\n"
            "Please confirm that you are human. In this chat enabled users filter.\n"
            "So if you don't answer to my question i will fe forced to remove you from this chat."
        ).format(users=", ".join(users.values())),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[buttons]),
    )
    await join_list.create_list(
        chat_id=message.chat.id, message_id=msg.message_id, users=users.keys()
    )
    return True


@dp.message_handler(content_types=types.ContentTypes.LEFT_CHAT_MEMBER)
async def left_chat_member(message: types.Message):
    # TODO: Remove user from join-list when user was left from chat
    raise SkipHandler


@dp.callback_query_handler(cb_join_list.filter())
async def cq_join_list(query: types.CallbackQuery, callback_data: dict):
    answer = callback_data["answer"]
    logger.info(
        "User {user} choose answer {answer} in join-list in chat {chat} and message {message}",
        user=query.from_user.id,
        chat=query.message.chat.id,
        answer=repr(answer),
        message=query.message.message_id,
    )
    in_list = await join_list.pop_user_from_list(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        user_id=query.from_user.id,
    )
    if not in_list:
        return await query.answer(_("This message is not for you!"), show_alert=True)

    if answer == "human":
        await query.answer(_("Good answer!"))
        await query.message.chat.restrict(
            query.from_user.id,
            permissions=types.ChatPermissions(can_send_messages=True),
            until_date=config.JOIN_NO_MEDIA_DURATION,
        )
    else:
        await query.answer(_("Bad answer."), show_alert=True)
        await asyncio.sleep(2)
        await query.message.chat.kick(query.from_user.id)
        await query.message.chat.unban(query.from_user.id)

    users_list = await join_list.check_list(
        chat_id=query.message.chat.id, message_id=query.message.message_id
    )
    if not users_list:
        with suppress(MessageToDeleteNotFound):
            await query.message.delete()

    return True
