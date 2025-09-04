from typing import Any, Dict, Optional
from engine.apiclient import BackendAPIClient
from engine.model_picker import ModelPicker


class QuerySender:
    def __init__(self, model_picker: ModelPicker, client: BackendAPIClient):
        self.model_picker = model_picker
        self.client = client

    async def execute(self, lang: Optional[str], model_requested: str, payload_json: Optional[bool], system_message: str, user_message: str) -> Dict[str, Any]:
        picked_model = await self.model_picker.consider_model(model_requested, lang)
        if picked_model is None:
            raise ValueError(f"Cannot find a model for request {model_requested}")
        task = await self.client.submit_task(
            picked_model,
            system_message,
            user_message,
            payload_json if payload_json else False,
        )
        task_id = task["id"]["id"]
        task_capability = task["id"]["cap"]
        awaiter = self.client.create_task_waiter(task_capability, task_id)
        result = await awaiter.wait_for_status()
        return result["output"]
