from typing import Optional, Any, List, get_args
from pydantic import BaseModel, Field, ConfigDict, field_serializer, model_validator
import copy

class OptionValue(BaseModel):
    optionType: str
    value: Optional[Any] = None
    model_config = ConfigDict(exclude_none=True)

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

class User(BaseModel):
    name: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    password: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    privilege: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value="15"))
    pubkeyChain: List[Any] = Field(default_factory=list)
    model_config = ConfigDict(exclude_none=True)

class Server(BaseModel):
    address: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    port: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=49))
    timeout: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=5))
    key: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    model_config = ConfigDict(exclude_none=True)

class Tacacs(BaseModel):
    groupName: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    vpn: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=0))
    sourceInterface: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    server: List[Server] = Field(default_factory=list)
    model_config = ConfigDict(exclude_none=True)

class AccountingRule(BaseModel):
    ruleId: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    method: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    level: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    startStop: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    group: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    model_config = ConfigDict(exclude_none=True)

class AuthorizationRule(BaseModel):
    ruleId: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    method: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    level: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    group: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default"))
    ifAuthenticated: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    model_config = ConfigDict(exclude_none=True)

class AaaData(BaseModel):
    authenticationGroup: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    accountingGroup: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    serverAuthOrder: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="global", value=["local"]))
    authorizationConsole: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    authorizationConfigCommands: Optional[OptionValue] = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    user: List[User] = Field(default_factory=list)
    radius: List[Any] = Field(default_factory=list)
    tacacs: List[Tacacs] = Field(default_factory=list)
    accountingRule: List[AccountingRule] = Field(default_factory=list)
    authorizationRule: List[AuthorizationRule] = Field(default_factory=list)
    model_config = ConfigDict(exclude_none=True)

class AaaModel(BaseModel):
    name: str
    description: str
    data: AaaData = Field(default_factory=AaaData)
    model_config = ConfigDict(exclude_none=True)

class AaaBuilder:
    def __init__(self, name: str, description: str):
        self.model = AaaModel(name=name, description=description)

    def set_path_option(self, path: str, field: str, option_type: str, value: Any):
        path_parts = path.split('.')
        
        # Remap special paths to standard model paths
        if path_parts[0] == 'aaa_root':
            path_parts.pop(0)
        elif path_parts[0] == 'tacacs_root':
            path_parts = ['tacacs', '0'] + path_parts[1:]
        elif path_parts[0] == 'tacacs_server':
            path_parts = ['tacacs', '0', 'server'] + path_parts[1:]

        # Start traversal from the data model
        target_obj = self.model.data
        parent_obj = self.model
        attr_on_parent = "data"

        for part in path_parts:
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
                attr_on_parent = None # Next part must be a field name
            else:
                parent_obj = target_obj
                attr_on_parent = part
                target_obj = getattr(target_obj, part)

        # Process value based on type and field name for API requirements
        processed_value = value
        if option_type == "variable" and value is not None:
            processed_value = f"{{{{{value}}}}}"
        else:
            # Specific type conversions required by the API for non-variable values
            string_fields = ['privilege', 'key', 'ruleId', 'level', 'sourceInterface']
            list_fields = ['group']

            if field in string_fields and processed_value is not None:
                processed_value = str(processed_value)
            
            if field in list_fields and processed_value is not None:
                if not isinstance(processed_value, list):
                    processed_value = [str(processed_value)]
                else:
                    processed_value = [str(item) for item in processed_value]

        # Create the final OptionValue and set it on the target object
        if option_type == "default":
            # Get the default from the Pydantic model field definition
            option = target_obj.model_fields[field].default_factory()
        else:
            option = OptionValue(optionType=option_type, value=processed_value)
        
        setattr(target_obj, field, option)

    def build(self) -> AaaModel:
        return copy.deepcopy(self.model)

    def json(self, **kwargs) -> str:
        return self.build().model_dump_json(exclude_none=True, by_alias=True, **kwargs)

    def dict(self, **kwargs) -> dict:
        return self.build().model_dump(exclude_none=True, by_alias=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/aaa"