import json
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from app.db import Database
from app.models import AuditLog, OrderRecord, utcnow

class AuditService:
    def __init__(self, db: Database): self.db = db
    async def write(self, action: str, target: str = "", detail: str = "", actor: str = "system") -> None:
        # Never put cookies or credentials in audit detail.
        async with self.db.sessions() as session:
            session.add(AuditLog(actor=actor, action=action, target=target, detail=detail[:2000]))
            await session.commit()
    async def recent(self, limit: int = 20) -> list[dict]:
        async with self.db.sessions() as session:
            rows = (await session.scalars(select(AuditLog).order_by(desc(AuditLog.id)).limit(limit))).all()
            return [{"id": r.id, "actor": r.actor, "action": r.action, "target": r.target, "detail": r.detail, "created_at": r.created_at.isoformat()} for r in rows]

class OrderService:
    def __init__(self, db: Database): self.db = db
    async def list(self, limit: int = 50) -> list[dict]:
        async with self.db.sessions() as session:
            rows = (await session.scalars(select(OrderRecord).order_by(desc(OrderRecord.id)).limit(min(max(limit, 1), 200)))).all()
            return [self.serialize(r) for r in rows]
    @staticmethod
    def serialize(row: OrderRecord) -> dict:
        return {"id": row.id, "platform": row.platform, "external_id": row.external_id, "title": row.title, "buyer": row.buyer, "amount": row.amount, "currency": row.currency, "status": row.status, "created_at": row.created_at.isoformat()}
    async def add_external(self, order: dict) -> bool:
        async with self.db.sessions() as session:
            record = OrderRecord(platform=str(order.get("platform", "playerok"))[:32], external_id=str(order["external_id"])[:128], title=str(order.get("title", "Unknown item"))[:500], buyer=str(order.get("buyer", "unknown"))[:128], amount=str(order.get("amount", "0"))[:64], currency=str(order.get("currency", "RUB"))[:8], status=str(order.get("status", "unknown"))[:64], payload_json=json.dumps({}, ensure_ascii=False), created_at=utcnow())
            session.add(record)
            try:
                await session.commit()
                return True
            except IntegrityError:
                await session.rollback()
                return False
    async def seed_demo(self) -> dict:
        import secrets
        order = {"platform": "demo", "external_id": "DEMO-" + secrets.token_hex(4).upper(), "title": "Демонстрационный цифровой товар", "buyer": "demo_buyer", "amount": "199.00", "currency": "RUB", "status": "paid_demo"}
        await self.add_external(order)
        return order
