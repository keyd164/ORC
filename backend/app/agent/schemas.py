from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator, field_validator

ToolName = Literal['summary', 'rooms', 'exceptions', 'bills', 'documents']


class Scope(BaseModel):
    start: date
    end: date
    room: str | None = Field(None, max_length=40)

    @model_validator(mode='after')
    def range_valid(self):
        if self.start > self.end:
            raise ValueError('起始日期不能晚于结束日期')
        if (self.end-self.start).days > 3660:
            raise ValueError('单次查询最多十年')
        return self


class Plan(BaseModel):
    scope: Scope
    tools: list[ToolName] = Field(min_length=1, max_length=5)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    mode: Literal['rules', 'ollama'] = 'rules'

    @field_validator('question')
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('请输入业务问题')
        return value
