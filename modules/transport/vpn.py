from typing import Any, List, Union, Optional
from pydantic import BaseModel, Field, field_serializer, model_validator

class OptionValue(BaseModel):
    optionType: str
    value: Union[str, int, bool, None] = None

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

class Prefix(BaseModel):
    ipAddress: OptionValue
    subnetMask: OptionValue

class NextHopEntry(BaseModel):
    address: OptionValue
    distance: OptionValue

class Ipv4RouteEntry(BaseModel):
    nextHop: List[NextHopEntry] = Field(default_factory=list)
    distance: OptionValue
    prefix: Prefix
    gateway: OptionValue

class VpnData(BaseModel):
    newHostMapping: List = Field(default_factory=list)
    ipv6Route: List = Field(default_factory=list)
    service: List = Field(default_factory=list)
    enhanceEcmpKeying: OptionValue
    vpnId: OptionValue
    ipv4Route: List[Ipv4RouteEntry] = Field(default_factory=list)

class VpnModel(BaseModel):
    name: str
    description: str
    data: VpnData

class VpnBuilder:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.data = {
            "newHostMapping": [],
            "ipv6Route": [],
            "service": [],
            "enhanceEcmpKeying": OptionValue(optionType="default", value=False),
            "vpnId": OptionValue(optionType="default", value=0),
            "ipv4Route": [],
        }

    def set_path_option(self, path: str, field: str, option_type: str, value: Any):
        """
        Set an option at a given path.
        The path is a dot-separated string representing the nested structure.
        An empty, None, or "vpn_root" path targets top-level fields.
        """
        path_str = str(path)
        if not path_str or path_str.lower() == 'nan' or path_str == "vpn_root":
            current_level = self.data
        else:
            current_level = self.data
            parts = path_str.split('.')
            for part in parts:
                if isinstance(current_level, dict):
                    current_level = current_level.get(part)
                elif isinstance(current_level, list):
                    try:
                        idx = int(part)
                        if idx >= len(current_level):
                            # This case should be handled by an 'add' method if we are creating new list items
                            raise IndexError(f"Index {idx} out of bounds for list at path '{path_str}'.")
                        current_level = current_level[idx]
                    except (ValueError, IndexError):
                        raise KeyError(f"Invalid list index '{part}' in path '{path_str}'")
                elif hasattr(current_level, part):
                    current_level = getattr(current_level, part)
                else:
                    raise KeyError(f"Unknown path component: '{part}' in path '{path_str}'")

                if current_level is None:
                    raise KeyError(f"Path '{path_str}' leads to a None value at component '{part}'.")

        target_object = current_level
        if hasattr(target_object, field):
            if isinstance(getattr(target_object, field), OptionValue):
                setattr(target_object, field, OptionValue(optionType=option_type, value=value))
            else:
                raise TypeError(f"Field '{field}' at path '{path_str}' is not an OptionValue field.")
        elif isinstance(target_object, dict) and field in target_object:
             if isinstance(target_object[field], OptionValue):
                target_object[field] = OptionValue(optionType=option_type, value=value)
             else:
                raise TypeError(f"Field '{field}' at path '{path_str}' is not a simple OptionValue field.")
        else:
            raise KeyError(f"Unknown field: '{field}' at path '{path_str}'")

    def add_ipv4_route(self, next_hops: List[dict], distance: tuple, prefix: dict, gateway: tuple):
        nh_list = [
            NextHopEntry(
                address=OptionValue(optionType=nh["address"][0], value=nh["address"][1]),
                distance=OptionValue(optionType=nh["distance"][0], value=nh["distance"][1])
            ) for nh in next_hops
        ]
        entry = Ipv4RouteEntry(
            nextHop=nh_list,
            distance=OptionValue(optionType=distance[0], value=distance[1]),
            prefix=Prefix(
                ipAddress=OptionValue(optionType=prefix["ipAddress"][0], value=prefix["ipAddress"][1]),
                subnetMask=OptionValue(optionType=prefix["subnetMask"][0], value=prefix["subnetMask"][1])
            ),
            gateway=OptionValue(optionType=gateway[0], value=gateway[1])
        )
        self.data["ipv4Route"].append(entry)

    def build(self) -> VpnModel:
        data_model = VpnData(**self.data)
        return VpnModel(
            name=self.name,
            description=self.description,
            data=data_model
        )

    def dict(self, **kwargs) -> dict:
        return self.build().model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        return self.build().model_dump_json(exclude_none=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/transport/{transportId}/wan/vpn"
    
