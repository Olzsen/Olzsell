import json
from sqlalchemy import select,desc
from sqlalchemy.exc import IntegrityError
from app.db import Database
from app.models import AuditLog,OrderRecord,utcnow
class AuditService:
    def __init__(self,db:Database): self.db=db
    async def write(self,action:str,target:str='',detail:str='',actor:str='system')->None:
        async with self.db.sessions() as s: s.add(AuditLog(actor=actor,action=action,target=target,detail=detail[:2000])); await s.commit()
    async def recent(self,limit:int=20)->list[dict]:
        async with self.db.sessions() as s:
            rows=(await s.scalars(select(AuditLog).order_by(desc(AuditLog.id)).limit(limit))).all()
            return [{'id':r.id,'actor':r.actor,'action':r.action,'target':r.target,'detail':r.detail,'created_at':r.created_at.isoformat()} for r in rows]
class OrderService:
    def __init__(self,db:Database): self.db=db
    async def list(self,limit:int=50)->list[dict]:
        async with self.db.sessions() as s:
            rows=(await s.scalars(select(OrderRecord).order_by(desc(OrderRecord.id)).limit(min(max(limit,1),200)))).all()
            return [self.serialize(r) for r in rows]
    @staticmethod
    def serialize(r:OrderRecord)->dict: return {'id':r.id,'platform':r.platform,'external_id':r.external_id,'title':r.title,'buyer':r.buyer,'amount':r.amount,'currency':r.currency,'status':r.status,'created_at':r.created_at.isoformat()}
    async def add_external(self,o:dict)->bool:
        async with self.db.sessions() as s:
            s.add(OrderRecord(platform=str(o.get('platform','playerok'))[:32],external_id=str(o['external_id'])[:128],title=str(o.get('title','Unknown item'))[:500],buyer=str(o.get('buyer','unknown'))[:128],amount=str(o.get('amount','0'))[:64],currency=str(o.get('currency','RUB'))[:8],status=str(o.get('status','unknown'))[:64],payload_json=json.dumps({},ensure_ascii=False),created_at=utcnow()))
            try: await s.commit(); return True
            except IntegrityError: await s.rollback(); return False
    async def seed_demo(self)->dict:
        import secrets
        o={'platform':'demo','external_id':'DEMO-'+secrets.token_hex(4).upper(),'title':'Демонстрационный цифровой товар','buyer':'demo_buyer','amount':'199.00','currency':'RUB','status':'paid_demo'}
        await self.add_external(o); return o
