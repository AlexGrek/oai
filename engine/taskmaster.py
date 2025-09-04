import logging
from typing import Any

from fastapi import Depends
from engine.apiclient import BackendAPIClient, get_async_api_client
from engine.model_picker import ModelPicker
from engine.pipelines.exec import PipelineExecutor
from engine.pipelines.query_send import QuerySender
from storage.pipelines import PipelineStorage

logger = logging.getLogger(__name__)

class Taskmaster:
    def __init__(self, backend_api_client: BackendAPIClient, storage_config: Any):
        self.client = backend_api_client
        self.model_picker = ModelPicker(self.client)
        self.query_sender = QuerySender(self.model_picker, self.client)
        self.pipeline_storage = PipelineStorage(storage_config)

    async def new_request(self, pipeline_name: str, input: Any):
        pipeline = await self.pipeline_storage.get_pipeline(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")
        executor = PipelineExecutor(pipeline, self.query_sender, self.client)
        return await executor.execute(input)


_client_instance = None


async def get_async_taskmaster(
    client: BackendAPIClient = Depends(get_async_api_client),
) -> Taskmaster:
    """
    This dependency function provides a singleton instance of BackendAPIClient.
    The instance is created only on the first request it's needed.
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = Taskmaster(client, {})

    return _client_instance
