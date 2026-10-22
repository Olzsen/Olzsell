import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from pydantic import ValidationError

from app.api import create_app
from app.bot import register_handlers
from app.config import Settings
from app.db import Database
from app.playerok_config import load_playerok_settings
from app.plugins import PluginManager
from app.services import AuditService, OrderService
from app.telegram_context import TelegramContext


async def main() -> None:
    try:
        settings = Settings()
        load_playerok_settings(settings)
    except (ValidationError, RuntimeError) as exc:
        raise SystemExit(f"Invalid configuration: {exc}") from exc

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("olzsell")

    db = Database(settings.database_url)
    await db.initialize()
    audit = AuditService(db)
    orders = OrderService(db)
    plugins = PluginManager(settings, audit, orders)
    await plugins.discover_bundled()

    session = AiohttpSession(proxy=settings.telegram_proxy or None)
    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        session=session,
    )
    dp = Dispatcher()
    register_handlers(dp, TelegramContext(settings, bot, plugins, orders, audit))

    api = create_app(settings, db, plugins, orders, audit)
    server = uvicorn.Server(
        uvicorn.Config(
            api,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            access_log=False,
        )
    )
    server_task = asyncio.create_task(server.serve())
    retry_delay = 3

    try:
        logger.info("Starting Olzsell on %s:%s", settings.host, settings.port)
        if settings.telegram_proxy:
            logger.info("Telegram proxy is configured")
        while True:
            try:
                await dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                )
                break
            except TelegramNetworkError as exc:
                logger.warning(
                    "Telegram API is unreachable: %s. Retrying in %s seconds; "
                    "the local API will remain available.",
                    exc,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
    finally:
        server.should_exit = True
        await server_task
        await plugins.shutdown()
        await bot.session.close()
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
