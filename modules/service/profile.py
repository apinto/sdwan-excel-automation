from pydantic import BaseModel


class ServiceProfile(BaseModel):
    name: str
    description: str


class ServiceProfileBuilder:
    def __init__(self, name: str, description: str):
        self.name = name
        self._model = ServiceProfile(name=name, description=description)

    def build(self) -> ServiceProfile:
        return self._model

    def dict(self) -> dict:
        return self._model.model_dump()

    def json(self) -> str:
        return self._model.model_dump_json(indent=2)
    
    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/service/"
