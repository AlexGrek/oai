from typing import Optional
from engine.apiclient import BackendAPIClient


class ModelPicker:
    def __init__(self, backend_api_client: BackendAPIClient):
        self.client = backend_api_client

    async def consider_model(self, request: str, lang: Optional[str]):
        available = await self.client.check_capabilities_online()
        usable = [x for x in available if x.startswith("LLM::")]
        # TODO: add some actual logic
        if len(usable) > 0:
            return usable[0]
        else:
            return None