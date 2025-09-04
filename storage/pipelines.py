from typing import Any, Optional

import yaml

from engine.pipelines.models import Pipeline

yaml_pipeline = """
name: "My lovely LLM pipeline"
steps:
  - action: query
    json: true
    model: any
    lang: en
    message:
      chat_history: []
      system: "You are a logs analyzer. Return a JSON with 3 fields: {suspicious: float[0-1], security_risk: boolean, reason: string}"
      user: "Analyze log line: '${input}'"
    extract:
      - name: result_all
        jq: "."
      - name: sec_risk
        jq: ".security_risk"
        type: boolean
      - name: suspicious_coef
        jq: ".suspicious"
        type: number
  - action: query
    if:
      - a: suspicious_coef
        op: gt
        b: 0.75
        and: 
          - a: sec_risk
            op: is
            b: true
    json: false
    model: any/strong
    message:
      system: "You are a helpful assistant"
      user: "You have got a log line: ${input}. Another LLM thinks that this is suspicious because of security risk and says: ${result_all.reason}. What do you think? Explain."
    extract: 
      - name: expert_response
        fulltext: true
"""

class PipelineStorage:
    def __init__(self, storage_config: Any):
        pass

    async def get_pipeline(self, name: str) -> Optional[Pipeline]:
        pipeline_dict = yaml.safe_load(yaml_pipeline)
        pipeline_model = Pipeline.model_validate(pipeline_dict)
        return pipeline_model
