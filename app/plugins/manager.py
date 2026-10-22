import importlib.util,logging,re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any
from app.config import Settings
from app.services import AuditService,OrderService
logger=logging.getLogger(__name__); VALID_ID=re.compile(r'^[a-z][a-z0-9_-]{1,39}$')
@dataclass
class PluginContext:
    settings:Settings
    audit:AuditService
    orders:OrderService
class PluginBase:
    plugin_id='plugin'; name='Unnamed plugin'; version='0.0.0'
    def __init__(self): self.enabled=False; self.ctx:PluginContext|None=None
    async def on_load(self,ctx:PluginContext)->None: self.ctx=ctx
    async def on_unload(self)->None: self.enabled=False
    async def on_order(self,order:dict[str,Any])->None: return None
    def telegram_buttons(self)->list[dict[str,str]]: return []
@dataclass
class PluginEntry:
    plugin:PluginBase
    source:str
    path:Path|None=None
    module:ModuleType|None=None
    approved:bool=True
class PluginManager:
    def __init__(self,settings:Settings,audit:AuditService,orders:OrderService):
        self.settings=settings; self.context=PluginContext(settings,audit,orders); self.audit=audit; self.orders=orders; self.entries:dict[str,PluginEntry]={}; self.pending:dict[str,Path]={}; settings.plugins_dir.mkdir(parents=True,exist_ok=True)
    async def discover_bundled(self)->None:
        for p in sorted(self.settings.plugins_dir.glob('*/plugin.py')): await self._load_file(p,'bundled',True)
        for p in self.settings.plugins_dir.glob('uploaded_*.py'):
            pid=p.stem.removeprefix('uploaded_')
            if VALID_ID.fullmatch(pid): self.pending[pid]=p
    async def _load_file(self,p:Path,source:str,enabled_default:bool)->None:
        code=p.read_text(encoding='utf-8'); compile(code,str(p),'exec')
        spec=importlib.util.spec_from_file_location(f'olzsell_plugin_{p.parent.name}_{p.stem}',p)
        if spec is None or spec.loader is None: raise RuntimeError('Cannot load plugin')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        classes=[o for o in module.__dict__.values() if isinstance(o,type) and issubclass(o,PluginBase) and o is not PluginBase]
        if len(classes)!=1: raise ValueError('A plugin must define exactly one PluginBase subclass')
        plugin=classes[0](); pid=getattr(plugin,'plugin_id','')
        if not VALID_ID.fullmatch(pid): raise ValueError('Invalid plugin id')
        if pid in self.entries: raise ValueError('Duplicate plugin id')
        self.entries[pid]=PluginEntry(plugin,source,p,module,True); await plugin.on_load(self.context)
        if enabled_default: plugin.enabled=True
        logger.info('Registered plugin %s (%s)',pid,source)
    async def enable(self,pid:str)->None:
        e=self.entries.get(pid)
        if e: e.plugin.enabled=True; return
        p=self.pending.get(pid)
        if p is None: raise KeyError(pid)
        # Enabling uploaded Python executes arbitrary code with this process's permissions.
        await self._load_file(p,'uploaded',True); self.pending.pop(pid,None)
    async def disable(self,pid:str)->None:
        e=self.entries.get(pid)
        if e is None:
            if pid in self.pending: self.pending.pop(pid,None); return
            raise KeyError(pid)
        await e.plugin.on_unload(); e.plugin.enabled=False
    def get(self,pid:str)->PluginBase|None:
        e=self.entries.get(pid); return e.plugin if e else None
    def list_plugins(self)->list[dict[str,Any]]:
        items=[{'plugin_id':pid,'name':e.plugin.name,'version':e.plugin.version,'enabled':e.plugin.enabled,'source':e.source,'approved':e.approved} for pid,e in self.entries.items()]
        items.extend({'plugin_id':pid,'name':f'Загруженный плагин: {pid}','version':'не проверен','enabled':False,'source':'uploaded_pending','approved':False} for pid in self.pending)
        return items
    async def save_uploaded(self,filename:str,raw:bytes)->str:
        if len(raw)>self.settings.max_plugin_upload_mb*1024*1024 or len(raw)>1_000_000: raise ValueError('File too large')
        if not filename.endswith('.py'): raise ValueError('Only .py files accepted')
        source=raw.decode('utf-8'); compile(source,filename,'exec')
        slug=re.sub(r'[^a-z0-9_-]+','_',Path(filename).stem.lower()).strip('_-'); slug=re.sub(r'_+','_',slug)[:30].strip('_-')
        if not slug: raise ValueError('Invalid filename')
        p=self.settings.plugins_dir/f'uploaded_{slug}.py'; p.write_text(source,encoding='utf-8'); self.pending[slug]=p; return slug
    async def remove_uploaded(self,pid:str)->bool:
        e=self.entries.get(pid)
        if e and e.source!='uploaded': return False
        if e:
            await e.plugin.on_unload(); self.entries.pop(pid,None)
            if e.path: e.path.unlink(missing_ok=True)
            return True
        p=self.pending.pop(pid,None)
        if p: p.unlink(missing_ok=True); return True
        return False
    async def shutdown(self)->None:
        for pid,e in list(self.entries.items()):
            try: await e.plugin.on_unload()
            except Exception: logger.exception('Plugin unload failed: %s',pid)
