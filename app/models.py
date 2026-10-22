from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

def utcnow() -> datetime: return datetime.now(timezone.utc)
class OrderRecord(Base):
    __tablename__='orders'
    __table_args__=(UniqueConstraint('platform','external_id',name='uq_order_external'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    platform:Mapped[str]=mapped_column(String(32),default='playerok',index=True)
    external_id:Mapped[str]=mapped_column(String(128),index=True)
    title:Mapped[str]=mapped_column(String(500),default='Unknown item')
    buyer:Mapped[str]=mapped_column(String(128),default='unknown')
    amount:Mapped[str]=mapped_column(String(64),default='0')
    currency:Mapped[str]=mapped_column(String(8),default='RUB')
    status:Mapped[str]=mapped_column(String(64),default='unknown',index=True)
    payload_json:Mapped[str]=mapped_column(Text,default='{}')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class PluginRecord(Base):
    __tablename__='plugins'
    plugin_id:Mapped[str]=mapped_column(String(80),primary_key=True)
    name:Mapped[str]=mapped_column(String(120))
    version:Mapped[str]=mapped_column(String(40),default='0.0.0')
    enabled:Mapped[int]=mapped_column(Integer,default=0)
    source:Mapped[str]=mapped_column(String(20),default='bundled')
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
class AuditLog(Base):
    __tablename__='audit_logs'
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    actor:Mapped[str]=mapped_column(String(128),default='system')
    action:Mapped[str]=mapped_column(String(128),index=True)
    target:Mapped[str]=mapped_column(String(256),default='')
    detail:Mapped[str]=mapped_column(Text,default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
