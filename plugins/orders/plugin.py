from app.plugins import PluginBase,PluginContext
class OrdersPlugin(PluginBase):
    plugin_id='orders'; name='Обработка заказов'; version='0.1.0'
    async def on_load(self,ctx:PluginContext)->None: await super().on_load(ctx)
    async def on_order(self,order:dict)->None:
        # Extension point for verified Playerok events; no remote actions are performed yet.
        if self.ctx: await self.ctx.audit.write('order.observed',str(order.get('external_id','unknown'))[:128],'Observed locally; no external mutation performed')
    def telegram_buttons(self)->list[dict[str,str]]: return [{'text':'📦 Показать заказы','callback_data':'menu:orders'}]
