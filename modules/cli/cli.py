from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_serializer, model_validator

class OptionValue(BaseModel):
    optionType: str
    value: Optional[Any] = None
    model_config = ConfigDict(exclude_none=True, populate_by_name=True)

class CliData(BaseModel):
    config: str
    model_config = ConfigDict(populate_by_name=True, exclude_none=True)

class CliModel(BaseModel):
    name: str
    data: CliData
    model_config = ConfigDict(exclude_none=True)

class CliBuilder:
    def __init__(self, name: str, config: str):
        self.model = CliModel(name=name, data=CliData(config=config))

    def set_config(self, config: str):
        self.model.data.config = config
        return self

    def build(self) -> CliModel:
        return self.model

    def dict(self) -> dict:
        return self.model.model_dump(exclude_none=True)

    def json(self) -> str:
        return self.model.model_dump_json(indent=2, exclude_none=True)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/cli/{cliId}/config"


