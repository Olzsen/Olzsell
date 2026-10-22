import importlib.util
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any
from app.config import Settings
from app.services import AuditService, OrderService

logger = logging.getLogger(__name__)
VALID_ID = re.compile(r"^[a-z][a-z0-9_-]{1,39}$")

@dataclass
class PluginContext:
    settings: Settings
    audit: AuditService
    orders: OrderService

class PluginBase:
    plugin_id = "plugin"
    name = "Unnamed plugin"
    version = "0.0.0"
    def __init__(self) -> None:
        self.enabled = False
        self.ctx: PluginContext | None = None
    async def on_load(self, ctx: PluginContext) -> None: self.ctx = ctx
    async def on_unload(self) -> None: self.enabled = False
    async def on_order(self, order: dict[str, Any]) -> None: return None
    def telegram_buttons(self) -> list[dict[str, str]]: return []

@dataclass
class PluginEntry:
    plugin: PluginBase
    source: str
    path: Path | None = None
    module: ModuleType | None = None
    approved: bool = True

class PluginManager:
    def __init__(self, settings: Settings, audit: AuditService, orders: OrderService):
        self.settings = settings; self.context = PluginContext(settings, audit, orders)
        self.audit = audit; self.orders = orders; self.entries: dict[str, PluginEntry] = {}; self.pending: dict[str, Path] = {}
        settings.plugins_dir.mkdir(parents=True, exist_ok=True)
    async def discover_bundled(self) -> None:
        for path in sorted(self.settings.plugins_dir.glob("*/plugin.py")):
            await self._load_file(path, source="bundled", enabled_default=True)
        for path in self.settings.plugins_dir.glob("uploaded_*.py"):
            safe_id = path.stem.removeprefix("uploaded_")
            if VALID_ID.fullmatch(safe_id): self.pending[safe_id] = path
    async def _load_file(self, path: Path, source: str, enabled_default: bool) -> None:
        code = path.read_text(encoding="utf-8"); compile(code, str(path), "exec")
        module_name = f"olzsell_plugin_{path.parent.name}_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None: raise RuntimeError("Cannot load plugin")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        candidates = [obj for obj in module.__dict__.values() if isinstance(obj, type) and issubclass(obj, PluginBase) and obj is not PluginBase]
        if len(candidates) != 1: raise ValueError("A plugin must define exactly one PluginBase subclass")
        plugin = candidates[0](); plugin_id = getattr(plugin, "plugin_id", "")
        if not VALID_ID.fullmatch(plugin_id): raise ValueError("Invalid plugin_id")
        if plugin_id in self.entries: raise ValueError("Duplicate plugin id")
        self.entries[plugin_id] = PluginEntry(plugin, source, path, module, True)
        await plugin.on_load(self.context)
        if enabled_default: plugin.enabled = True
        logger.info("Registered plugin %s (%s)", plugin_id, source)
    async def enable(self, plugin_id: str) -> None:
        entry = self.entries.get(plugin_id)
        if entry: entry.plugin.enabled = True; return
        path = self.pending.get(plugin_id)
        if path is None: raise KeyError(plugin_id)
        await self._load_file(path, source="uploaded", enabled_default=True); self.pending.pop(plugin_id, None)
    async def disable(self, plugin_id: str) -> None:
        entry = self.entries.get(plugin_id)
        if entry is None:
            if plugin_id in self.pending: self.pending.pop(plugin_id, None); return
            raise KeyError(plugin_id)
        await entry.plugin.on_unload(); entry.plugin.enabled = False
    def get(self, plugin_id: str) -> PluginBase | None:
        entry = self.entries.get(plugin_id); return entry.plugin if entry else None
    def list_plugins(self) -> list[dict[str, Any]]:
        items = [{"plugin_id": pid, "name": e.plugin.name, "version": e.plugin.version, "enabled": e.plugin.enabled, "source": e.source, "approved": e.approved} for pid, e in self.entries.items()]
        items.extend({"plugin_id": pid, "name": f"Загруженный плагин: {pid}", "version": "не проверен", "enabled": False, "source": "uploaded_pending", "approved": False} for pid in self.pending)
        return items
    async def save_uploaded(self, filename: str, raw: bytes) -> str:
        if len(raw) > self.settings.max_plugin_upload_mb * 1024 * 1024: raise ValueError("File too large")
        if not filename.endswith(".py") or len(raw) > 1_000_000: raise ValueError("Only small Python source files are accepted")
        source = raw.decode("utf-8"); compile(source, filename, "exec")
        slug = re.sub(r"[^a-z0-9_-]+", "_", Path(filename).stem.lower()).strip("_-")
        slug = re.sub(r"_+", "_", slug)[:30].strip("_-")
        if not slug: raise ValueError("Invalid plugin filename")
        safe_name = re.sub(r"[^a-z0-9_-]", "_", slug)[:30]
        path = self.settings.plugins_dir / f"uploaded_{safe_name}.py"
        path.write_text(source, encoding="utf-8"); self.pending[safe_name] = path
        return safe_name
    async def remove_uploaded(self, plugin_id: str) -> bool:
        entry = self.entries.get(plugin_id)
        if entry and entry.source != "uploaded": return False
        if entry:
            await entry.plugin.on_unload(); self.entries.pop(plugin_id, None)
            if entry.path: entry.path.unlink(missing_ok=True)
            return True
        path = self.pending.pop(plugin_id, None)
        if path: path.unlink(missing_ok=True); return True
        return False
    async def shutdown(self) -> None:
        for plugin_id, entry in list(self.entries.items()):
            try: await entry.plugin.on_unload()
            except Exception: logger.exception("Plugin unload failed: %s", plugin_id)
