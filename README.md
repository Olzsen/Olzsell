# Olzsell

Модульный Telegram-бот для автоматизации продавца на Playerok. По удобству панели и файловым плагинам ориентируемся на [FunPayCardinal](https://github.com/sidor0912/FunPayCardinal), но проект и код самостоятельные.

**Статус:** стартовая реализация. Есть админ-панель Telegram, собственный FastAPI, SQLite/PostgreSQL-ready слой SQLAlchemy, загрузка Python-файлов плагинов, журнал действий и демо-заказы. Реальная интеграция Playerok в этом коммите ещё не подключена: живые заказы не подтверждаются/не меняются и автовыдачи нет.

## Playerok: как работает токен

В неофициальных клиентах Playerok используется cookie `token` домена `.playerok.com`. В зависимости от выбранной библиотеки и защиты площадки могут также потребоваться cookies защиты DDoS-Guard и такой же User-Agent/IP, как у сессии браузера. Детали меняются, поэтому сверяйте конкретную версию библиотеки с её документацией: [auth](https://playerok-api.readthedocs.io/ru/stable/guide/auth.html), [transports](https://playerok-api.readthedocs.io/ru/stable/guide/transports.html), [источник неофициального клиента](https://github.com/treyder17/PlayerokAPI).

1. Залогиньтесь на Playerok в браузере.
2. Откройте DevTools → Application/Storage → Cookies → `https://playerok.com`.
3. Найдите `token` и положите значение в `PLAYEROK_TOKEN` в локальном `.env`.
4. Если документация конкретной библиотеки требует дополнительные cookie/User-Agent, храните их только в `.env` или секретном хранилище.
5. Не присылайте токены/cookies в чат, не коммитьте их в GitHub и не выводите в логи. Эти значения могут дать доступ к сессии аккаунта.

## Запуск в Windows PowerShell

Требуется Python 3.11+ и Git.

```powershell
git clone https://github.com/Olzsen/Olzsell.git
cd Olzsell
py -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python -m app
```

## Запуск Linux/macOS

```bash
git clone https://github.com/Olzsen/Olzsell.git
cd Olzsell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python -m app
```

В `.env` заполните `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID` (ваш числовой Telegram ID), `API_KEY` (рандомная строка не короче 32 символов). `PLAYEROK_TOKEN` пока опционален: стартовый адаптер не делает запросов к Playerok.

Отправьте боту `/start`. Кнопки открывают разделы «Плагины», «Заказы», «Статус», «Логи». Нажмите «Демо-заказ», чтобы проверить базу без реальной покупки.

## API

API слушает `127.0.0.1:8000` по умолчанию. Swagger: `http://127.0.0.1:8000/docs`. `/health` открыт, всем `/api/v1/*` нужен заголовок `X-API-Key`.

```bash
curl http://127.0.0.1:8000/health
curl -H "X-API-Key: YOUR_API_KEY" http://127.0.0.1:8000/api/v1/plugins
curl -X POST -H "X-API-Key: YOUR_API_KEY" http://127.0.0.1:8000/api/v1/orders/demo
curl -H "X-API-Key: YOUR_API_KEY" http://127.0.0.1:8000/api/v1/orders
```

Основные endpoints: `GET /api/v1/plugins`, `POST /api/v1/plugins/{plugin_id}/enable`, `POST /api/v1/plugins/{plugin_id}/disable`, `GET /api/v1/orders`, `POST /api/v1/orders/demo`, `GET /api/v1/audit`.

## Плагины

- Встроенные плагины расположены в `plugins/<id>/plugin.py` и наследуются от `app.plugins.PluginBase`.
- Можно отправить `.py`-файл боту. Он сохраняется как pending и не запускается автоматически.
- Включать можно только доверенный код: Python-плагин работает с правами всего процесса бота. Проверка имени/размера/синтаксиса не является песочницей.
- Плагинный контракт поддерживает `on_load(ctx)`, `on_unload()`, `on_order(order)` и `telegram_buttons()`.

## Docker

```bash
cp .env.example .env
# запишите секреты в .env
mkdir -p data logs
docker compose up --build -d
docker compose logs -f
```

Сервис API привязан к localhost. Для удалённого доступа используйте HTTPS reverse proxy и firewall; не публикуйте API без защиты.

## Хранилище и CI

По умолчанию SQLite (`data/olzsell.db`). Для PostgreSQL задайте `DATABASE_URL=postgresql+asyncpg://user:password@host:5432/olzsell` и обеспечьте миграцию/бэкап данных. GitHub Actions проверяет компиляцию и базовые тесты.

## Чего пока нет

Реальные Playerok-запросы и stream событий не проверены на аккаунте: этот шаг требует зафиксировать версию клиента и подтвердить формат заказа. До этого нет автоответов продавцам, автоподтверждения сделки, автовыдачи, отмены заказа или платных операций. Неофициальные интерфейсы могут поменяться, а использование автоматизации должно соответствовать правилам площадки.
