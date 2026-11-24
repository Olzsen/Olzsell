import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards import main_menu
from app.bot.render import dashboard_text
from app.config import ensure_data_directory, get_settings


async def main() -> None:
    settings = get_settings()
    ensure_data_directory()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start_handler(message: Message) -> None:
        name = message.from_user.first_name if message.from_user else None
        await message.answer(
            dashboard_text(name),
            reply_markup=main_menu(),
        )

    logging.info("Telegram-бот запускается")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
