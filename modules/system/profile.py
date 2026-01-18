from pydantic import BaseModel


class SysProfile(BaseModel):
    name: str
    description: str


class SysProfileBuilder:
    def __init__(self, name: str, description: str):
        self.name = name
        self._model = SysProfile(name=name, description=description)

    def build(self) -> SysProfile:
        return self._model

    def dict(self) -> dict:
        return self._model.model_dump()

    def json(self) -> str:
        return self._model.model_dump_json(indent=2)
    
    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/system/"

'''
builder = SysProfileBuilder(
    name="SysProfile-ConfigGroup1-NY",
    description="Sys Profile for config group 1 for NY site"
)

print(builder.json())

print(builder.api_url())

'''