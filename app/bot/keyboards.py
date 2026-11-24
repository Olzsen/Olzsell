from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛍 Мои лоты", callback_data="lots:page:0"),
                InlineKeyboardButton(text="📦 Заказы", callback_data="orders:page:0"),
            ],
            [
                InlineKeyboardButton(text="💬 Сообщения", callback_data="chats:list"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats:overview"),
            ],
            [
                InlineKeyboardButton(text="🧩 Плагины", callback_data="plugins:list"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:main"),
            ],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="dashboard:refresh")],
        ]
    )
