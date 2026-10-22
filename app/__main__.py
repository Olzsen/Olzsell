import asyncio,logging
import uvicorn
from aiogram import Bot,Dispatcher
from pydantic import ValidationError
from app.api import create_app
from app.bot import register_handlers
from app.config import Settings
from app.db import Database
from app.plugins import PluginManager
from app.services import AuditService,OrderService
from app.telegram_context import TelegramContext
async def main()->None:
    try: settings=Settings()
    except ValidationError as exc: raise SystemExit(f'Invalid configuration: {exc}') from exc
    logging.basicConfig(level=getattr(logging,settings.log_level.upper(),logging.INFO),format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    db=Database(settings.database_url); await db.initialize()
    audit=AuditService(db); orders=OrderService(db); plugins=PluginManager(settings,audit,orders); await plugins.discover_bundled()
    bot=Bot(token=settings.telegram_bot_token.get_secret_value()); dp=Dispatcher(); register_handlers(dp,TelegramContext(settings,bot,plugins,orders,audit))
    api=create_app(settings,db,plugins,orders,audit); server=uvicorn.Server(uvicorn.Config(api,host=settings.host,port=settings.port,log_level=settings.log_level.lower(),access_log=False)); task=asyncio.create_task(server.serve())
    try: logging.getLogger('olzsell').info('Starting Olzsell on %s:%s',settings.host,settings.port); await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
    finally:
        server.should_exit=True; await task; await plugins.shutdown(); await bot.session.close(); await db.dispose()
if __name__=='__main__': asyncio.run(main())
