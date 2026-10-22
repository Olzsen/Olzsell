import html
import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from app.telegram_context import TelegramContext

logger = logging.getLogger(__name__)

def is_admin(ctx: TelegramContext, user_id: int | None) -> bool:
    return user_id is not None and user_id == ctx.settings.admin_telegram_id

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧩 Плагины", callback_data="menu:plugins"), InlineKeyboardButton(text="📦 Заказы", callback_data="menu:orders")],
        [InlineKeyboardButton(text="🩺 Статус", callback_data="menu:status"), InlineKeyboardButton(text="📜 Логи", callback_data="menu:logs")],
        [InlineKeyboardButton(text="➕ Демо-заказ", callback_data="orders:demo")],
    ])

def plugins_keyboard(ctx: TelegramContext) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{'🟢' if p['enabled'] else '⚪'} {p['name'][:35]}", callback_data=f"plugin:view:{p['plugin_id']}")] for p in ctx.plugins.list_plugins()]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def send_menu(message: Message, ctx: TelegramContext) -> None:
    await message.answer("🛠 <b>Olzsell</b>\nПанель управления автоматизацией Playerok.\n\nВыберите раздел:", reply_markup=main_keyboard(), parse_mode="HTML")

def register_handlers(dp, ctx: TelegramContext) -> None:
    router = Router()
    @router.message(Command("start", "menu"))
    async def start(message: Message):
        if not is_admin(ctx, message.from_user.id if message.from_user else None):
            await message.answer("⛔ Доступ закрыт."); return
        await send_menu(message, ctx)
    @router.message(Command("status"))
    async def status_command(message: Message):
        if not is_admin(ctx, message.from_user.id if message.from_user else None):
            return await message.answer("⛔ Доступ закрыт.")
        await message.answer(f"🩺 <b>Статус Olzsell</b>\nПлагины: {len(ctx.plugins.list_plugins())}\nPlayerok: режим <code>{html.escape(ctx.settings.playerok_mode)}</code>\nЖивые заказы: интеграция ещё не подключена.", parse_mode="HTML", reply_markup=main_keyboard())
    @router.callback_query(F.data.startswith("menu:"))
    async def menu_callback(query: CallbackQuery):
        if not is_admin(ctx, query.from_user.id):
            await query.answer("Нет доступа", show_alert=True); return
        action = query.data.split(":", 1)[1]
        if action == "home":
            await query.message.edit_text("🛠 <b>Olzsell</b>\nВыберите раздел:", parse_mode="HTML", reply_markup=main_keyboard())
        elif action == "plugins":
            await query.message.edit_text("🧩 <b>Управление плагинами</b>", parse_mode="HTML", reply_markup=plugins_keyboard(ctx))
        elif action == "orders":
            orders = await ctx.orders.list(20)
            body = "\n\n".join(f"#{o['id']} · <code>{html.escape(o['external_id'])}</code>\n{html.escape(o['title'][:80])}\n{html.escape(o['amount'])} {html.escape(o['currency'])} · {html.escape(o['status'])}" for o in orders) or "Пока нет заказов. Используйте «Демо-заказ» для проверки."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Обновить", callback_data="menu:orders")], [InlineKeyboardButton(text="➕ Демо-заказ", callback_data="orders:demo")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")]])
            await query.message.edit_text("📦 <b>Заказы</b>\n\n" + body, parse_mode="HTML", reply_markup=keyboard)
        elif action == "status":
            await query.message.edit_text(f"🩺 <b>Статус</b>\nРежим Playerok: <code>{html.escape(ctx.settings.playerok_mode)}</code>\nИнтеграция с реальными заказами не подключена.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")]]))
        elif action == "logs":
            rows = await ctx.audit.recent(10)
            body = "\n".join(f"#{x['id']} {html.escape(x['action'])} — {html.escape(x['target'])}" for x in rows) or "Лог пуст."
            await query.message.edit_text("📜 <b>Последние действия</b>\n\n" + body, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")]]))
        await query.answer()
    @router.callback_query(F.data == "orders:demo")
    async def demo_order(query: CallbackQuery):
        if not is_admin(ctx, query.from_user.id):
            await query.answer("Нет доступа", show_alert=True); return
        order = await ctx.orders.seed_demo()
        await ctx.audit.write("order.demo_created", order["external_id"], "Demo order created", str(query.from_user.id))
        await query.answer("Демо-заказ добавлен")
        await query.message.answer(f"✅ Демо-заказ <code>{html.escape(order['external_id'])}</code> создан. Это локальная тестовая запись, не реальная сделка Playerok.", parse_mode="HTML", reply_markup=main_keyboard())
    @router.callback_query(F.data.startswith("plugin:view:"))
    async def plugin_view(query: CallbackQuery):
        if not is_admin(ctx, query.from_user.id):
            await query.answer("Нет доступа", show_alert=True); return
        plugin_id = query.data.split(":", 2)[2]
        plugin = ctx.plugins.get(plugin_id)
        if plugin is None:
            await query.answer("Плагин не найден или ожидает проверки", show_alert=True); return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=("⏸ Отключить" if plugin.enabled else "▶️ Включить"), callback_data=f"plugin:toggle:{plugin_id}")], [InlineKeyboardButton(text="🗑 Удалить загруженный файл", callback_data=f"plugin:remove:{plugin_id}")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:plugins")]])
        await query.message.edit_text(f"🧩 <b>{html.escape(plugin.name)}</b>\nID: <code>{html.escape(plugin.plugin_id)}</code>\nВерсия: <code>{html.escape(plugin.version)}</code>\nСостояние: {'включён' if plugin.enabled else 'выключен'}\n\nPython-плагины выполняются с правами процесса бота.", parse_mode="HTML", reply_markup=keyboard)
        await query.answer()
    @router.callback_query(F.data.startswith("plugin:toggle:"))
    async def plugin_toggle(query: CallbackQuery):
        if not is_admin(ctx, query.from_user.id):
            await query.answer("Нет доступа", show_alert=True); return
        plugin_id = query.data.split(":", 2)[2]
        plugin = ctx.plugins.get(plugin_id)
        if plugin is None:
            await query.answer("Плагин не найден", show_alert=True); return
        try:
            if plugin.enabled:
                await ctx.plugins.disable(plugin_id); await ctx.audit.write("plugin.disabled", plugin_id, "Disabled from Telegram", str(query.from_user.id))
            else:
                await ctx.plugins.enable(plugin_id); await ctx.audit.write("plugin.enabled", plugin_id, "Enabled from Telegram", str(query.from_user.id))
        except Exception:
            logger.exception("Plugin toggle failed: %s", plugin_id)
            await query.answer("Не удалось изменить состояние", show_alert=True); return
        plugin = ctx.plugins.get(plugin_id)
        await query.answer("Готово")
        await query.message.edit_text(f"🧩 <b>{html.escape(plugin.name)}</b>\nID: <code>{html.escape(plugin_id)}</code>\nВерсия: <code>{html.escape(plugin.version)}</code>\nСостояние: {'включён' if plugin.enabled else 'выключен'}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=("⏸ Отключить" if plugin.enabled else "▶️ Включить"), callback_data=f"plugin:toggle:{plugin_id}")], [InlineKeyboardButton(text="⬅️ К плагинам", callback_data="menu:plugins")]]))
    @router.callback_query(F.data.startswith("plugin:remove:"))
    async def plugin_remove(query: CallbackQuery):
        if not is_admin(ctx, query.from_user.id):
            await query.answer("Нет доступа", show_alert=True); return
        plugin_id = query.data.split(":", 2)[2]
        try:
            removed = await ctx.plugins.remove_uploaded(plugin_id)
            await ctx.audit.write("plugin.removed" if removed else "plugin.remove_denied", plugin_id, "Uploaded plugin removal", str(query.from_user.id))
        except Exception:
            logger.exception("Plugin removal failed"); removed = False
        await query.answer("Удалено" if removed else "Удалить нельзя", show_alert=True)
        await query.message.edit_text("🧩 <b>Плагины</b>", parse_mode="HTML", reply_markup=plugins_keyboard(ctx))
    @router.message(F.document)
    async def uploaded_plugin(message: Message):
        if not is_admin(ctx, message.from_user.id if message.from_user else None):
            await message.answer("⛔ Доступ закрыт."); return
        doc = message.document
        if not doc.file_name or not doc.file_name.endswith(".py"):
            await message.answer("Пришлите файл плагина с расширением .py."); return
        max_bytes = ctx.settings.max_plugin_upload_mb * 1024 * 1024
        if doc.file_size and doc.file_size > max_bytes:
            await message.answer(f"Файл превышает лимит {ctx.settings.max_plugin_upload_mb} МБ."); return
        file = await ctx.bot.get_file(doc.file_id)
        downloaded = await ctx.bot.download_file(file.file_path)
        try:
            plugin_id = await ctx.plugins.save_uploaded(doc.file_name, downloaded.read())
            await ctx.audit.write("plugin.uploaded_pending", plugin_id, "Uploaded source saved pending review", str(message.from_user.id))
        except Exception as exc:
            logger.warning("Rejected plugin upload: %s", type(exc).__name__)
            await message.answer("Не удалось принять файл. Проверьте имя и формат."); return
        await message.answer(f"📥 Файл сохранён как <code>{html.escape(plugin_id)}</code>, но не запущен. Перед включением проверьте исходник: Python-код имеет права процесса бота.", parse_mode="HTML", reply_markup=main_keyboard())
    dp.include_router(router)
