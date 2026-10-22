import hmac
from fastapi import Depends,FastAPI,Header,HTTPException,Query,status
from fastapi.responses import JSONResponse
from app.config import Settings
from app.db import Database
from app.plugins import PluginManager
from app.services import AuditService,OrderService
def create_app(settings:Settings,db:Database,plugins:PluginManager,orders:OrderService,audit:AuditService)->FastAPI:
    app=FastAPI(title='Olzsell API',version='0.1.0',description='Personal API; /api/v1 endpoints require X-API-Key.')
    async def require_api_key(x_api_key:str|None=Header(default=None,alias='X-API-Key')):
        if not x_api_key or not hmac.compare_digest(x_api_key,settings.api_key.get_secret_value()): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Invalid API key')
    @app.get('/health')
    async def health(): return {'ok':True,'service':'olzsell','playerok_mode':settings.playerok_mode}
    @app.get('/api/v1/plugins',dependencies=[Depends(require_api_key)])
    async def list_plugins(): return {'items':plugins.list_plugins()}
    @app.post('/api/v1/plugins/{plugin_id}/enable',dependencies=[Depends(require_api_key)])
    async def enable_plugin(plugin_id:str):
        try: await plugins.enable(plugin_id)
        except KeyError: raise HTTPException(404,'Plugin not found')
        except Exception as exc: raise HTTPException(400,'Plugin could not be enabled') from exc
        await audit.write('plugin.enabled_api',plugin_id,'Enabled through API'); return {'ok':True,'plugin_id':plugin_id,'enabled':True}
    @app.post('/api/v1/plugins/{plugin_id}/disable',dependencies=[Depends(require_api_key)])
    async def disable_plugin(plugin_id:str):
        try: await plugins.disable(plugin_id)
        except KeyError: raise HTTPException(404,'Plugin not found')
        await audit.write('plugin.disabled_api',plugin_id,'Disabled through API'); return {'ok':True,'plugin_id':plugin_id,'enabled':False}
    @app.get('/api/v1/orders',dependencies=[Depends(require_api_key)])
    async def list_orders(limit:int=Query(default=50,ge=1,le=200)): return {'items':await orders.list(limit)}
    @app.post('/api/v1/orders/demo',dependencies=[Depends(require_api_key)])
    async def create_demo_order():
        item=await orders.seed_demo(); await audit.write('order.demo_created_api',item['external_id'],'Demo-only order created'); return JSONResponse(status_code=201,content=item)
    @app.get('/api/v1/audit',dependencies=[Depends(require_api_key)])
    async def list_audit(limit:int=Query(default=50,ge=1,le=200)): return {'items':await audit.recent(limit)}
    return app
