# YAML definition from the prompt
import asyncio
import json

import yaml

from engine.pipelines.exec import PipelineExecutor
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

async def main():
    # 1. Load and parse the YAML into Pydantic models
    pipeline_dict = yaml.safe_load(yaml_pipeline)
    pipeline_model = Pipeline.model_validate(pipeline_dict)

    # 2. Create and run the executor
    executor = PipelineExecutor(pipeline_model)
    log_line_input = "127.0.0.1 - admin [10/Oct/2000:13:55:36 -0700] 'GET /index.php?user=admin' UNION SELECT 1,2,3 -- ' HTTP/1.0' 200 45"
    
    final_context = await executor.execute(initial_input=log_line_input)
    
    print("\n--- FINAL CONTEXT ---")
    print(json.dumps(final_context, indent=2))

if __name__ == "__main__":
    asyncio.run(main())