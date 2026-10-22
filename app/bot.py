import html
import json
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pydantic import SecretStr

from app.playerok_config import save_playerok_settings
from app.telegram_context import TelegramContext

logger = logging.getLogger(__name__)


def is_admin(ctx: TelegramContext, user_id: int | None) -> bool:
    return user_id is not None and user_id == ctx.settings.admin_telegram_id


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧩 Плагины", callback_data="menu:plugins"),
            InlineKeyboardButton(text="📦 Заказы", callback_data="menu:orders"),
        ],
        [
            InlineKeyboardButton(text="🩺 Статус", callback_data="menu:status"),
            InlineKeyboardButton(text="📜 Логи", callback_data="menu:logs"),
        ],
        [InlineKeyboardButton(text="⚙️ Настройки Playerok", callback_data="menu:playerok")],
        [InlineKeyboardButton(text="➕ Демо-заказ", callback_data="orders:demo")],
    ])


def plugins_keyboard(ctx: TelegramContext) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{'🟢' if p['enabled'] else '⚪'} {p['name'][:35]}",
            callback_data=f"plugin:view:{p['plugin_id']}",
        )]
        for p in ctx.plugins.list_plugins()
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def playerok_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Установить токен", callback_data="pok:set:token")],
        [InlineKeyboardButton(text="🧭 Установить User-Agent", callback_data="pok:set:ua")],
        [InlineKeyboardButton(text="🍪 Дополнительные cookies (JSON)", callback_data="pok:set:cookies")],
        [InlineKeyboardButton(text="🧹 Очистить токен", callback_data="pok:clear:token")],
        [InlineKeyboardButton(text="🧹 Очистить User-Agent/cookies", callback_data="pok:clear:extras")],
        [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="menu:playerok")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")],
    ])


def playerok_status(ctx: TelegramContext) -> str:
    token_set = bool(ctx.settings.playerok_token and ctx.settings.playerok_token.get_secret_value())
    ua_set = bool(ctx.settings.playerok_user_agent.strip())
    cookies_set = bool(
        ctx.settings.playerok_extra_cookies_json
        and ctx.settings.playerok_extra_cookies_json.get_secret_value()
    )
    return (
        "⚙️ <b>Настройки Playerok</b>\n\n"
        f"Токен: {'✅ сохранён' if token_set else '❌ не задан'}\n"
        f"User-Agent: {'✅ задан' if ua_set else 'не задан'}\n"
        f"Дополнительные cookies: {'✅ сохранены' if cookies_set else 'не заданы'}\n"
        f"Режим конфигурации: <code>{html.escape(ctx.settings.playerok_mode)}</code>\n\n"
        "Секреты не показываются в сообщениях. Значения сохраняются локально в data/playerok_settings.json.\n\n"
        "Важно: текущая версия Olzsell ещё не подключает реальный клиент Playerok. Эти настройки сохраняются, но сами по себе не включают получение реальных заказов или автовыдачу."
    )


async def send_menu(message: Message, ctx: TelegramContext) -> None:
    await message.answer(
        "🛠 <b>Olzsell</b>\nПанель управления автоматизацией Playerok.\n\nВыберите раздел:",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )


def register_handlers(dp, ctx: TelegramContext) -> None:
    router = Router()

    @router.message(Command("start", "menu"))
    async def start(message: Message):
        if not is_admin(ctx, message.from_user.id if message.from_user else None):
            await message.answer("⛔ Доступ закрыт.")
            return
        await send_menu(message, ctx)

    @router.message(Command("status"))
    async def status_command(message: Message):
        if not is_admin(ctx, message.from_user.id if message.from_user else None):
            await message.answer("⛔ Доступ закрыт.")
            return
        await message.answer(
            f"🩺 <b>Статус Olzsell</b>\nПлагины: {len(ctx.plugins.list_plugins())}\n"
            f"Playerok: <code>{html.escape(ctx.settings.playerok_mode)}</code>\n"
            "Реальные заказы: интеграция ещё не подключена.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    @router.callback_query(F.data.startswith("menu:"))
    async def menu_callback(q: CallbackQuery):
        if not is_admin(ctx, q.from_user.id):
            await q.answer("Нет доступа", show_alert=True)
            return
        action = q.data.split(":", 1)[1]
        if action == "home":
            await q.message.edit_text(
                "🛠 <b>Olzsell</b>\nВыберите раздел:",
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
        elif action == "playerok":
            await q.message.edit_text(
                playerok_status(ctx),
                parse_mode="HTML",
                reply_markup=playerok_keyboard(),
            )
        elif action == "plugins":
            await q.message.edit_text(
                "🧩 <b>Управление плагинами</b>",
                parse_mode="HTML",
                reply_markup=plugins_keyboard(ctx),
            )
        elif action == "orders":
            items = await ctx.orders.list(20)
            body = "\n\n".join(
                f"#{o['id']} · <code>{html.escape(o['external_id'])}</code>\n"
                f"{html.escape(o['title'][:80])}\n"
                f"{html.escape(o['amount'])} {html.escape(o['currency'])} · {html.escape(o['status'])}"
                for o in items
            ) or "Пока нет заказов. Создайте демо-заказ для проверки."
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="menu:orders")],
                [InlineKeyboardButton(text="➕ Демо-заказ", callback_data="orders:demo")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")],
            ])
            await q.message.edit_text("📦 <b>Заказы</b>\n\n" + body, parse_mode="HTML", reply_markup=kb)
        elif action == "status":
            await q.message.edit_text(
                f"🩺 <b>Статус</b>\nPlayerok: <code>{html.escape(ctx.settings.playerok_mode)}</code>\n"
                "Live-интеграция не подключена.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ Настройки Playerok", callback_data="menu:playerok")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")],
                ]),
            )
        elif action == "logs":
            rows = await ctx.audit.recent(10)
            body = "\n".join(
                f"#{x['id']} {html.escape(x['action'])} — {html.escape(x['target'])}"
                for x in rows
            ) or "Лог пуст."
            await q.message.edit_text(
                "📜 <b>Последние действия</b>\n\n" + body,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")]
                ]),
            )
        await q.answer()

    @router.callback_query(F.data.startswith("pok:set:"))
    async def playerok_set_start(q: CallbackQuery):
        if not is_admin(ctx, q.from_user.id):
            await q.answer("Нет доступа", show_alert=True)
            return
        field = q.data.rsplit(":", 1)[1]
        ctx.pending_settings[q.from_user.id] = field
        prompts = {
            "token": "Отправь одним сообщением cookie token Playerok. Не пересылай его никому. Сообщение будет удалено ботом, если Telegram позволит.",
            "ua": "Отправь полный User-Agent браузера. Для отмены нажми /cancel.",
            "cookies": 'Отправь дополнительные cookies в JSON, например {"ddg5":"значение"}. Если они не нужны — нажми /cancel.',
        }
        await q.message.answer(
            prompts[field] + "\n\n/cancel — отменить ввод.",
            parse_mode="HTML",
        )
        await q.answer()

    @router.message(Command("cancel"))
    async def cancel_setting(message: Message):
        if not is_admin(ctx, message.from_user.id if message.from_user else None):
            return
        ctx.pending_settings.pop(message.from_user.id, None)
        await message.answer("Ввод отменён.", reply_markup=main_keyboard())

    @router.callback_query(F.data.startswith("pok:clear:"))
    async def playerok_clear(q: CallbackQuery):
        if not is_admin(ctx, q.from_user.id):
            await q.answer("Нет доступа", show_alert=True)
            return
        what = q.data.rsplit(":", 1)[1]
        if what == "token":
            ctx.settings.playerok_token = None
            await ctx.audit.write("playerok.token_cleared", "playerok", "Token cleared in Telegram settings", str(q.from_user.id))
        else:
            ctx.settings.playerok_user_agent = ""
            ctx.settings.playerok_extra_cookies_json = None
            await ctx.audit.write("playerok.extras_cleared", "playerok", "Extra settings cleared in Telegram", str(q.from_user.id))
        save_playerok_settings(ctx.settings)
        await q.answer("Настройки очищены")
        await q.message.edit_text(playerok_status(ctx), parse_mode="HTML", reply_markup=playerok_keyboard())

    @router.message(F.text)
    async def playerok_setting_value(message: Message):
        if not message.from_user or not is_admin(ctx, message.from_user.id):
            return
        field = ctx.pending_settings.get(message.from_user.id)
        if not field:
            return
        value = (message.text or "").strip()
        if value == "/cancel":
            ctx.pending_settings.pop(message.from_user.id, None)
            await message.answer("Ввод отменён.")
            return
        if not value:
            await message.answer("Пустое значение. Отправь значение или /cancel.")
            return
        if field == "cookies":
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()):
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                await message.answer('Неверный JSON. Пример: {"ddg5":"значение"}. Попробуй ещё раз или /cancel.')
                return
        try:
            if field == "token":
                ctx.settings.playerok_token = SecretStr(value)
                audit_action = "playerok.token_updated"
            elif field == "ua":
                ctx.settings.playerok_user_agent = value
                audit_action = "playerok.user_agent_updated"
            else:
                ctx.settings.playerok_extra_cookies_json = SecretStr(value)
                audit_action = "playerok.cookies_updated"
            save_playerok_settings(ctx.settings)
            await ctx.audit.write(audit_action, "playerok", "Credential changed through Telegram settings", str(message.from_user.id))
        except Exception:
            logger.exception("Could not save Playerok settings")
            await message.answer("Не удалось сохранить настройки. Проверь права на запись в папку проекта.")
            return
        ctx.pending_settings.pop(message.from_user.id, None)
        if field == "token":
            try:
                await message.delete()
            except Exception:
                pass
        await message.answer(
            "✅ Настройка сохранена локально. Значение секрета не будет отображаться в панели.\n\n"
            + playerok_status(ctx),
            parse_mode="HTML",
            reply_markup=playerok_keyboard(),
        )

    @router.callback_query(F.data == "orders:demo")
    async def demo_order(q: CallbackQuery):
        if not is_admin(ctx, q.from_user.id):
            await q.answer("Нет доступа", show_alert=True)
            return
        o = await ctx.orders.seed_demo()
        await ctx.audit.write("order.demo_created", o["external_id"], "Demo order created", str(q.from_user.id))
        await q.answer("Демо-заказ добавлен")
        await q.message.answer(
            f"✅ Демо-заказ <code>{html.escape(o['external_id'])}</code> создан. Это локальная тестовая запись, не сделка Playerok.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    @router.callback_query(F.data.startswith("plugin:view:"))
    async def plugin_view(q: CallbackQuery):
        if not is_admin(ctx, q.from_user.id):
            await q.answer("Нет доступа", show_alert=True)
            return
        pid = q.data.split(":", 2)[2]
        p = ctx.plugins.get(pid)
        if p is None:
            await q.answer("Плагин не найден или ожидает проверки", show_alert=True)
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=("⏸ Отключить" if p.enabled else "▶️ Включить"), callback_data=f"plugin:toggle:{pid}")],
            [InlineKeyboardButton(text="🗑 Удалить загруженный файл", callback_data=f"plugin:remove:{pid}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:plugins")],
        ])
        await q.message.edit_text(
            f"🧩 <b>{html.escape(p.name)}</b>\nID: <code>{html.escape(pid)}</code>\n"
            f"Версия: <code>{html.escape(p.version)}</code>\nСостояние: {'включён' if p.enabled else 'выключен'}\n\n"
            "Python-плагины работают с правами процесса бота.",
            parse_mode="HTML",
            reply_markup=kb,
        )
        await q.answer()

    @router.callback_query(F.data.startswith("plugin:toggle:"))
    async def toggle(q: CallbackQuery):
        if not is_admin(ctx, q.from_user.id):
            await q.answer("Нет доступа", show_alert=True)
            return
        pid = q.data.split(":", 2)[2]
        p = ctx.plugins.get(pid)
        if p is None:
            await q.answer("Плагин не найден", show_alert=True)
            return
        try:
            if p.enabled:
                await ctx.plugins.disable(pid)
                await ctx.audit.write("plugin.disabled", pid, "Disabled in Telegram", str(q.from_user.id))
            else:
                await ctx.plugins.enable(pid)
                await ctx.audit.write("plugin.enabled", pid, "Enabled in Telegram", str(q.from_user.id))
        except Exception:
            logger.exception("Plugin toggle failed: %s", pid)
            await q.answer("Не удалось изменить состояние", show_alert=True)
            return
        p = ctx.plugins.get(pid)
        await q.answer("Готово")
        await q.message.edit_text(
            f"🧩 <b>{html.escape(p.name)}</b>\nID: <code>{html.escape(pid)}</code>\n"
            f"Состояние: {'включён' if p.enabled else 'выключен'}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=("⏸ Отключить" if p.enabled else "▶️ Включить"), callback_data=f"plugin:toggle:{pid}")],
                [InlineKeyboardButton(text="⬅️ К плагинам", callback_data="menu:plugins")],
            ]),
        )

    @router.callback_query(F.data.startswith("plugin:remove:"))
    async def remove(q: CallbackQuery):
        if not is_admin(ctx, q.from_user.id):
            await q.answer("Нет доступа", show_alert=True)
            return
        pid = q.data.split(":", 2)[2]
        try:
            removed = await ctx.plugins.remove_uploaded(pid)
            await ctx.audit.write("plugin.removed" if removed else "plugin.remove_denied", pid, "Uploaded plugin removal", str(q.from_user.id))
        except Exception:
            logger.exception("Plugin removal failed")
            removed = False
        await q.answer("Удалено" if removed else "Удалить нельзя", show_alert=True)
        await q.message.edit_text("🧩 <b>Плагины</b>", parse_mode="HTML", reply_markup=plugins_keyboard(ctx))

    @router.message(F.document)
    async def upload(message: Message):
        if not is_admin(ctx, message.from_user.id if message.from_user else None):
            await message.answer("⛔ Доступ закрыт.")
            return
        doc = message.document
        if not doc.file_name or not doc.file_name.endswith(".py"):
            await message.answer("Пришлите файл плагина .py.")
            return
        max_bytes = ctx.settings.max_plugin_upload_mb * 1024 * 1024
        if doc.file_size and doc.file_size > max_bytes:
            await message.answer("Файл превышает лимит размера.")
            return
        f = await ctx.bot.get_file(doc.file_id)
        stream = await ctx.bot.download_file(f.file_path)
        try:
            pid = await ctx.plugins.save_uploaded(doc.file_name, stream.read())
            await ctx.audit.write("plugin.uploaded_pending", pid, "Saved pending review", str(message.from_user.id))
        except Exception as exc:
            logger.warning("Plugin upload rejected: %s", type(exc).__name__)
            await message.answer("Файл не принят: проверьте имя и синтаксис.")
            return
        await message.answer(
            f"📥 Файл <code>{html.escape(pid)}</code> сохранён, но не запущен. Проверьте его исходник перед включением: Python-код не изолирован.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    dp.include_router(router)
