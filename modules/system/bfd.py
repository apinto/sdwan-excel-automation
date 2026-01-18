from typing import Optional, Any, List, get_args
from pydantic import BaseModel, Field, ConfigDict,field_serializer, model_validator
import copy

class OptionValue(BaseModel):
    optionType: str
    value: Optional[Any] = None
    model_config = ConfigDict(exclude_none=True, populate_by_name=True)

    @field_serializer("value")
    def serialize_value(self, v):
        if self.optionType == "variable" and isinstance(v, str):
            if not v.startswith("{{") and not v.endswith("}}"):
                return f"{{{{{v}}}}}"
        return v
    
    @model_validator(mode="after")
    def validate_option(self):
        if self.optionType == "default":
            pass
        elif self.optionType == "global":
            if self.value is None:
                raise ValueError("OptionType 'global' requires an explicit value.")
        elif self.optionType == "variable":
            if not isinstance(self.value, str):
                raise ValueError("OptionType 'variable' requires a string value.")
        return self

class Color(BaseModel):
    color: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    hello_interval: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=1000), alias="helloInterval")
    multiplier: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=7))
    pmtu_discovery: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=False), alias="pmtuDiscovery")
    dscp: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=48))
    model_config = ConfigDict(populate_by_name=True, exclude_none=True)

class BfdData(BaseModel):
    multiplier: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=6))
    poll_interval: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=600000), alias="pollInterval")
    default_dscp: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=48), alias="defaultDscp")
    colors: List[Color] = Field(default_factory=list)
    model_config = ConfigDict(populate_by_name=True, exclude_none=True)

class BfdModel(BaseModel):
    name: str
    description: str
    data: BfdData = Field(default_factory=BfdData)
    model_config = ConfigDict(exclude_none=True)

class BfdBuilder:
    def __init__(self, name: str, description: str):
        self.model = BfdModel(name=name, description=description)

    def set_path_option(self, path: str, field: str, option_type: str, value: Any):
        """
        Sets an option on a nested Pydantic model within the builder's data structure.
        """
        target_obj = self.model
        parts = path.split('.')

        if path == '':
            parts = []

        parent_obj = None
        attr_on_parent = None

        for part in parts:
            if part.isdigit():
                idx = int(part)
                if attr_on_parent is None:
                    raise ValueError("Invalid path: consecutive numbers in path are not supported for nested lists without an intermediate field.")
                
                list_obj = getattr(parent_obj, attr_on_parent)
                
                field_info = parent_obj.model_fields[attr_on_parent]
                item_type = get_args(field_info.annotation)[0]
                
                while len(list_obj) <= idx:
                    list_obj.append(item_type())
                
                target_obj = list_obj[idx]
                parent_obj = target_obj
                attr_on_parent = None
            else:
                parent_obj = target_obj
                attr_on_parent = part
                target_obj = getattr(target_obj, part)

        processed_value = value
        if option_type == "variable" and value is not None:
            processed_value = f"{{{{{value}}}}}"
        elif isinstance(value, str):
            if value.lower() == 'true':
                processed_value = True
            elif value.lower() == 'false':
                processed_value = False
        
        field_to_set = field
        for f_name, f_info in target_obj.model_fields.items():
            if f_info.alias == field:
                field_to_set = f_name
                break

        if hasattr(target_obj, field_to_set):
            option = OptionValue(optionType=option_type, value=processed_value)
            setattr(target_obj, field_to_set, option)
        else:
            raise AttributeError(f"'{type(target_obj).__name__}' object has no attribute '{field_to_set}'")

    def build(self) -> BfdModel:
        return copy.deepcopy(self.model)

    def json(self, **kwargs) -> str:
        return self.build().model_dump_json(exclude_none=True, by_alias=True, **kwargs)

    def dict(self, **kwargs) -> dict:
        return self.build().model_dump(exclude_none=True, by_alias=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/bfd"