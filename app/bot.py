import html,logging
from aiogram import F,Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery,InlineKeyboardButton,InlineKeyboardMarkup,Message
from app.telegram_context import TelegramContext
logger=logging.getLogger(__name__)
def is_admin(ctx:TelegramContext,user_id:int|None)->bool: return user_id is not None and user_id==ctx.settings.admin_telegram_id
def main_keyboard()->InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🧩 Плагины',callback_data='menu:plugins'),InlineKeyboardButton(text='📦 Заказы',callback_data='menu:orders')],[InlineKeyboardButton(text='🩺 Статус',callback_data='menu:status'),InlineKeyboardButton(text='📜 Логи',callback_data='menu:logs')],[InlineKeyboardButton(text='➕ Демо-заказ',callback_data='orders:demo')]])
def plugins_keyboard(ctx:TelegramContext)->InlineKeyboardMarkup:
    rows=[[InlineKeyboardButton(text=f"{'🟢' if p['enabled'] else '⚪'} {p['name'][:35]}",callback_data=f"plugin:view:{p['plugin_id']}")] for p in ctx.plugins.list_plugins()]
    rows.append([InlineKeyboardButton(text='⬅️ Назад',callback_data='menu:home')]); return InlineKeyboardMarkup(inline_keyboard=rows)
async def send_menu(message:Message,ctx:TelegramContext)->None: await message.answer('🛠 <b>Olzsell</b>\nПанель управления автоматизацией Playerok.\n\nВыберите раздел:',reply_markup=main_keyboard(),parse_mode='HTML')
def register_handlers(dp,ctx:TelegramContext)->None:
    router=Router()
    @router.message(Command('start','menu'))
    async def start(message:Message):
        if not is_admin(ctx,message.from_user.id if message.from_user else None): await message.answer('⛔ Доступ закрыт.'); return
        await send_menu(message,ctx)
    @router.message(Command('status'))
    async def status_command(message:Message):
        if not is_admin(ctx,message.from_user.id if message.from_user else None): await message.answer('⛔ Доступ закрыт.'); return
        await message.answer(f"🩺 <b>Статус Olzsell</b>\nПлагины: {len(ctx.plugins.list_plugins())}\nPlayerok: <code>{html.escape(ctx.settings.playerok_mode)}</code>\nРеальные заказы: интеграция ещё не подключена.",parse_mode='HTML',reply_markup=main_keyboard())
    @router.callback_query(F.data.startswith('menu:'))
    async def menu_callback(q:CallbackQuery):
        if not is_admin(ctx,q.from_user.id): await q.answer('Нет доступа',show_alert=True); return
        action=q.data.split(':',1)[1]
        if action=='home': await q.message.edit_text('🛠 <b>Olzsell</b>\nВыберите раздел:',parse_mode='HTML',reply_markup=main_keyboard())
        elif action=='plugins': await q.message.edit_text('🧩 <b>Управление плагинами</b>',parse_mode='HTML',reply_markup=plugins_keyboard(ctx))
        elif action=='orders':
            items=await ctx.orders.list(20); body='\n\n'.join(f"#{o['id']} · <code>{html.escape(o['external_id'])}</code>\n{html.escape(o['title'][:80])}\n{html.escape(o['amount'])} {html.escape(o['currency'])} · {html.escape(o['status'])}" for o in items) or 'Пока нет заказов. Создайте демо-заказ для проверки.'
            kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Обновить',callback_data='menu:orders')],[InlineKeyboardButton(text='➕ Демо-заказ',callback_data='orders:demo')],[InlineKeyboardButton(text='⬅️ Назад',callback_data='menu:home')]])
            await q.message.edit_text('📦 <b>Заказы</b>\n\n'+body,parse_mode='HTML',reply_markup=kb)
        elif action=='status': await q.message.edit_text(f"🩺 <b>Статус</b>\nPlayerok: <code>{html.escape(ctx.settings.playerok_mode)}</code>\nLive-интеграция не подключена.",parse_mode='HTML',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад',callback_data='menu:home')]]))
        elif action=='logs':
            rows=await ctx.audit.recent(10); body='\n'.join(f"#{x['id']} {html.escape(x['action'])} — {html.escape(x['target'])}" for x in rows) or 'Лог пуст.'
            await q.message.edit_text('📜 <b>Последние действия</b>\n\n'+body,parse_mode='HTML',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад',callback_data='menu:home')]]))
        await q.answer()
    @router.callback_query(F.data=='orders:demo')
    async def demo_order(q:CallbackQuery):
        if not is_admin(ctx,q.from_user.id): await q.answer('Нет доступа',show_alert=True); return
        o=await ctx.orders.seed_demo(); await ctx.audit.write('order.demo_created',o['external_id'],'Demo order created',str(q.from_user.id)); await q.answer('Демо-заказ добавлен')
        await q.message.answer(f"✅ Демо-заказ <code>{html.escape(o['external_id'])}</code> создан. Это локальная тестовая запись, не сделка Playerok.",parse_mode='HTML',reply_markup=main_keyboard())
    @router.callback_query(F.data.startswith('plugin:view:'))
    async def plugin_view(q:CallbackQuery):
        if not is_admin(ctx,q.from_user.id): await q.answer('Нет доступа',show_alert=True); return
        pid=q.data.split(':',2)[2]; p=ctx.plugins.get(pid)
        if p is None: await q.answer('Плагин не найден или ожидает проверки',show_alert=True); return
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=('⏸ Отключить' if p.enabled else '▶️ Включить'),callback_data=f'plugin:toggle:{pid}')],[InlineKeyboardButton(text='🗑 Удалить загруженный файл',callback_data=f'plugin:remove:{pid}')],[InlineKeyboardButton(text='⬅️ Назад',callback_data='menu:plugins')]])
        await q.message.edit_text(f"🧩 <b>{html.escape(p.name)}</b>\nID: <code>{html.escape(pid)}</code>\nВерсия: <code>{html.escape(p.version)}</code>\nСостояние: {'включён' if p.enabled else 'выключен'}\n\nPython-плагины работают с правами процесса бота.",parse_mode='HTML',reply_markup=kb); await q.answer()
    @router.callback_query(F.data.startswith('plugin:toggle:'))
    async def toggle(q:CallbackQuery):
        if not is_admin(ctx,q.from_user.id): await q.answer('Нет доступа',show_alert=True); return
        pid=q.data.split(':',2)[2]; p=ctx.plugins.get(pid)
        if p is None: await q.answer('Плагин не найден',show_alert=True); return
        try:
            if p.enabled: await ctx.plugins.disable(pid); await ctx.audit.write('plugin.disabled',pid,'Disabled in Telegram',str(q.from_user.id))
            else: await ctx.plugins.enable(pid); await ctx.audit.write('plugin.enabled',pid,'Enabled in Telegram',str(q.from_user.id))
        except Exception:
            logger.exception('Plugin toggle failed: %s',pid); await q.answer('Не удалось изменить состояние',show_alert=True); return
        p=ctx.plugins.get(pid); await q.answer('Готово')
        await q.message.edit_text(f"🧩 <b>{html.escape(p.name)}</b>\nID: <code>{html.escape(pid)}</code>\nСостояние: {'включён' if p.enabled else 'выключен'}",parse_mode='HTML',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=('⏸ Отключить' if p.enabled else '▶️ Включить'),callback_data=f'plugin:toggle:{pid}')],[InlineKeyboardButton(text='⬅️ К плагинам',callback_data='menu:plugins')]]))
    @router.callback_query(F.data.startswith('plugin:remove:'))
    async def remove(q:CallbackQuery):
        if not is_admin(ctx,q.from_user.id): await q.answer('Нет доступа',show_alert=True); return
        pid=q.data.split(':',2)[2]
        try: removed=await ctx.plugins.remove_uploaded(pid); await ctx.audit.write('plugin.removed' if removed else 'plugin.remove_denied',pid,'Uploaded plugin removal',str(q.from_user.id))
        except Exception: logger.exception('Plugin removal failed'); removed=False
        await q.answer('Удалено' if removed else 'Удалить нельзя',show_alert=True); await q.message.edit_text('🧩 <b>Плагины</b>',parse_mode='HTML',reply_markup=plugins_keyboard(ctx))
    @router.message(F.document)
    async def upload(message:Message):
        if not is_admin(ctx,message.from_user.id if message.from_user else None): await message.answer('⛔ Доступ закрыт.'); return
        doc=message.document
        if not doc.file_name or not doc.file_name.endswith('.py'): await message.answer('Пришлите файл плагина .py.'); return
        max_bytes=ctx.settings.max_plugin_upload_mb*1024*1024
        if doc.file_size and doc.file_size>max_bytes: await message.answer('Файл превышает лимит размера.'); return
        f=await ctx.bot.get_file(doc.file_id); stream=await ctx.bot.download_file(f.file_path)
        try: pid=await ctx.plugins.save_uploaded(doc.file_name,stream.read()); await ctx.audit.write('plugin.uploaded_pending',pid,'Saved pending review',str(message.from_user.id))
        except Exception as exc: logger.warning('Plugin upload rejected: %s',type(exc).__name__); await message.answer('Файл не принят: проверьте имя и синтаксис.'); return
        await message.answer(f"📥 Файл <code>{html.escape(pid)}</code> сохранён, но не запущен. Проверьте его исходник перед включением: Python-код не изолирован.",parse_mode='HTML',reply_markup=main_keyboard())
    dp.include_router(router)
