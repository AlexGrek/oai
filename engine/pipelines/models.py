import asyncio
import json
import re
from typing import Any, List, Dict, Optional, Literal

import yaml
from pydantic import BaseModel, Field

# Using forward reference for recursive model
class Condition(BaseModel):
    a: str
    op: Literal["gt", "lt", "eq", "is", "is_not", "contains"]
    b: Any
    # Use alias because 'and' and 'or' are Python keywords
    and_: Optional[List['Condition']] = Field(None, alias='and')
    or_: Optional[List['Condition']] = Field(None, alias='or')


class Message(BaseModel):
    chat_history: List[Dict[str, str]] = []
    system: str
    user: str


class ExtractRule(BaseModel):
    name: str
    jq: Optional[str] = None
    fulltext: Optional[bool] = None
    type: Optional[Literal["string", "number", "boolean"]] = None


class Step(BaseModel):
    action: str
    if_condition: Optional[List[Condition]] = Field(None, alias='if')
    json: Optional[bool] = False
    model: Optional[str] = None
    lang: Optional[str] = None
    message: Optional[Message] = None
    extract: Optional[List[ExtractRule]] = None


class Pipeline(BaseModel):
    name: str
    steps: List[Step]

# Allow Condition to resolve the forward reference
Condition.model_rebuild()
