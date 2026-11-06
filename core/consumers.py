import json
 
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
 
from .services import MembershipService
 
 
class TaskNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        self.group_name = f"project_{self.project_id}"
        self.user = self.scope["user"]
 
        # Solo usuarios autenticados y miembros del proyecto
        if not self.user.is_authenticated:
            await self.close()
            return
        es_miembro = await database_sync_to_async(MembershipService.is_member)(
            self.user, self.project_id
        )
        if not es_miembro:
            await self.close()
            return
 
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        self.joined = True
 
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "presence_update", "payload": {"user": self.user.username, "status": "online"}},
        )
 
    async def disconnect(self, close_code):
        # Si la conexión fue rechazada en connect, nunca entró al grupo
        if not getattr(self, "joined", False):
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "presence_update", "payload": {"user": self.user.username, "status": "offline"}},
        )
 
    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({"echo": data}))
 
    async def task_notification(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
 
    async def presence_update(self, event):
        await self.send(text_data=json.dumps(event["payload"]))