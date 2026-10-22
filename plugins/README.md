# Plugins

Put bundled trusted plugins in a subdirectory with a `plugin.py` entry point, e.g. `plugins/orders/plugin.py`.

Uploaded `.py` files are saved and shown as pending review; they are not auto-executed. Only enable trusted Python plugins. A plugin runs in the same interpreter and has the same OS permissions as Olzsell: file upload and syntax validation are not a security sandbox.

Contract: subclass `app.plugins.PluginBase`, set `plugin_id`, `name`, `version`, and implement `on_load(ctx)`, `on_unload()`, optional `on_order(order)`, and optional `telegram_buttons()`.
Never log cookies, tokens, credentials, private messages or complete raw response payloads.
