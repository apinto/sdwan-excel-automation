from pydantic import BaseModel


class CliProfile(BaseModel):
    name: str
    description: str


class CliProfileBuilder:
    def __init__(self, name: str, description: str):
        self.name = name
        self._model = CliProfile(name=name, description=description)

    def build(self) -> CliProfile:
        return self._model

    def dict(self) -> dict:
        return self._model.model_dump()

    def json(self) -> str:
        return self._model.model_dump_json(indent=2)
    
    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/cli/"