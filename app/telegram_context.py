from dataclasses import dataclass
from aiogram import Bot
from app.config import Settings
from app.plugins import PluginManager
from app.services import AuditService, OrderService

@dataclass
class TelegramContext:
    settings: Settings
    bot: Bot
    plugins: PluginManager
    orders: OrderService
    audit: AuditService
