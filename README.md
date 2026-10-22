# Olzsell

Модульный Telegram-бот для автоматизации работы продавца на Playerok. Архитектурная идея вдохновлена удобством управления и файловыми плагинами FunPayCardinal, но код проекта самостоятельный.

> **Статус:** начальная реализация. Playerok интеграция пока изолирована за адаптером: поставляемый плагин работает в demo-режиме и не подтверждает, не отменяет и не изменяет реальные заказы. У неофициальных API-клиентов могут меняться внутренние контракты.

## Возможности основы

- Telegram-панель для одного администратора: меню на inline-кнопках.
- FastAPI с API-key авторизацией.
- SQLite по умолчанию, модель данных на SQLAlchemy позволяет переключиться на PostgreSQL через `DATABASE_URL`.
- Плагины из каталога `plugins/` и загрузка Python-файла через Telegram.
- Плагинный контракт с командами, кнопками управления, настройками и lifecycle.
- Журнал действий, ограничения размеров загружаемых файлов, проверка имени плагина.
- Конфигурация через переменные окружения; секреты и cookies не коммитятся.
- Демо-заказы для проверки панели без подключения к реальным данным.

## Что нужно для подключения Playerok

Неофициальные библиотеки обычно используют cookie `token` из домена `.playerok.com`. У некоторых конфигураций защита DDoS-Guard может требовать дополнительные cookies, а запросы должны идти с совместимыми IP и User-Agent. Точные детали зависят от библиотеки и меняются вместе с площадкой.

1. Войдите в свой аккаунт Playerok в браузере.
2. В инструментах разработчика откройте Application/Storage → Cookies → `https://playerok.com`.
3. Скопируйте значение cookie `token` в локальный `.env` (никогда не в GitHub/чат).
4. Если выбранная библиотека требует дополнительных cookies или User-Agent, используйте документированную ею конфигурацию и держите все значения локально.
5. Учитывайте, что это неофициальный интерфейс: он может измениться или блокировать автоматизацию. Не делайте обход ограничений доступа и не передавайте cookies третьим лицам.

Ссылки для изучения:
- [PlayerokAPI auth guide](https://playerok-api.readthedocs.io/ru/stable/guide/auth.html)
- [PlayerokAPI transports](https://playerok-api.readthedocs.io/ru/stable/guide/transports.html)
- [Unofficial PlayerokAPI source](https://github.com/treyder17/PlayerokAPI)
- [FunPayCardinal reference project](https://github.com/sidor0912/FunPayCardinal)

## Быстрый старт

Требуется Python 3.11+.

```bash
git clone https://github.com/Olzsen/Olzsell.git
cd Olzsell
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`: `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `API_KEY`, опционально `PLAYEROK_TOKEN`. Затем:

```bash
python -m app
```

Веб API доступен по `http://127.0.0.1:8000/docs`. Не публикуйте API наружу без HTTPS, firewall и смены примеров секретов.

## API

Все `/api/v1/*` endpoints требуют заголовок `X-API-Key`, кроме `/health`.

- `GET /health` — health check.
- `GET /api/v1/plugins` — список плагинов.
- `POST /api/v1/plugins/{plugin_id}/enable` — включить плагин.
- `POST /api/v1/plugins/{plugin_id}/disable` — отключить плагин.
- `GET /api/v1/orders` — список локально сохранённых/демо-заказов.
- `POST /api/v1/orders/demo` — создать демонстрационный заказ.

## Плагины

Плагины — исполняемый Python-код. Загружайте только доверенные файлы: один плагин имеет права процесса бота. Загрузка проверяет имя, расширение и лимит размера, но **не делает чужой Python-код безопасным**. Для публичного много-пользовательского хостинга нужно отдельное изолированное выполнение плагинов.

Ожидаемый контракт:

```python
from app.plugins import PluginBase, PluginContext

class ExamplePlugin(PluginBase):
    plugin_id = "example"
    name = "Example plugin"
    version = "1.0.0"

    async def on_load(self, ctx: PluginContext) -> None: ...
    async def on_unload(self) -> None: ...
    def telegram_buttons(self): ...
```

## Безопасность

- `.env`, database, logs, cookies и реальные данные — локальные, не коммитить.
- Telegram-обработчики доступны только `ADMIN_TELEGRAM_ID`.
- API ключ сравнивается в постоянном времени.
- Не отправляйте значения Playerok cookies в Telegram-логи.
- Реальные финансовые/торговые действия должны требовать отдельного явного подтверждения администратора и идемпотентной обработки.

## Текущий предел

Сейчас Orders plugin использует демо-данные. Включение живого Playerok требует выбрать и проверить конкретную версию клиента, подтвердить список сделок/заказов и формат событий. Автоматическая выдача, подтверждение получения, отмена, поднятие лотов или любые платные операции намеренно не реализованы без верифицированных контрактов.
