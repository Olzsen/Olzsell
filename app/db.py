from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase): pass
class Database:
    def __init__(self, url: str):
        if url.startswith('sqlite+aiosqlite:///'):
            path=url.removeprefix('sqlite+aiosqlite:///')
            if path and path != ':memory:':
                p=Path(path)
                if not p.is_absolute(): p=Path.cwd()/p
                p.parent.mkdir(parents=True,exist_ok=True)
        self.engine=create_async_engine(url,pool_pre_ping=True,connect_args={'timeout':30} if url.startswith('sqlite') else {})
        self.sessions=async_sessionmaker(self.engine,class_=AsyncSession,expire_on_commit=False)
    async def initialize(self)->None:
        from app.models import AuditLog, OrderRecord, PluginRecord
        async with self.engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async def dispose(self)->None: await self.engine.dispose()
