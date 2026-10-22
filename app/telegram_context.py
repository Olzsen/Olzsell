from dataclasses import dataclass, field

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
    pending_settings: dict[int, str] = field(default_factory=dict)
