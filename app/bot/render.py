from html import escape


def dashboard_text(username: str | None = None) -> str:
    """Главная панель. Значения динамических данных будут добавлены из сервисов."""
    greeting = f", {escape(username)}" if username else ""
    return (
        "✨ <b>FunPay Telegram</b>\n"
        f"Рады видеть{greeting}!\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🟢 <b>Состояние:</b> готов к подключению\n"
        "💰 <b>Баланс:</b> —\n"
        "📦 <b>Активные лоты:</b> —\n"
        "🛒 <b>Заказы:</b> —\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите нужный раздел:"
    )


def monospace_table(headers: list[str], rows: list[list[object]]) -> str:
    """Безопасная компактная таблица для Telegram HTML."""
    safe_headers = [escape(str(value)) for value in headers]
    safe_rows = [[escape(str(value)) for value in row] for row in rows]
    widths = [
        max(
            len(safe_headers[index]),
            *(len(row[index]) for row in safe_rows if index < len(row)),
        )
        for index in range(len(safe_headers))
    ]

    def line(values: list[str]) -> str:
        return " │ ".join(
            value[:widths[index]].ljust(widths[index])
            for index, value in enumerate(values[: len(widths)])
        )

    output = [line(safe_headers), "─┼─".join("─" * width for width in widths)]
    output.extend(line(row) for row in safe_rows)
    return "<pre>" + escape("\n".join(output)) + "</pre>"
