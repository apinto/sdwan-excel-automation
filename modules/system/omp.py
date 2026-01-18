from typing import Optional, Any, List, get_args
from pydantic import BaseModel, Field, ConfigDict, field_serializer, model_validator
import copy
import re

def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

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

class AdvertiseProtocol(BaseModel):
    bgp: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    ospf: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    connected: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    static: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    eigrp: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    lisp: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    isis: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    model_config = ConfigDict(populate_by_name=True, exclude_none=True)

class AdvertiseProtocolIpv4(AdvertiseProtocol):
    ospfv3: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))

class AdvertiseProtocolIpv6(AdvertiseProtocol):
    pass

class OmpData(BaseModel):
    graceful_restart: OptionValue = Field(alias="gracefulRestart", 
        default_factory=lambda: OptionValue(optionType="default", value=True))
    overlay_as: OptionValue = Field(alias="overlayAs",
        default_factory=lambda: OptionValue(optionType="default"))
    send_path_limit: OptionValue = Field(alias="sendPathLimit",
        default_factory=lambda: OptionValue(optionType="default", value=4))
    ecmp_limit: OptionValue = Field(alias="ecmpLimit",
        default_factory=lambda: OptionValue(optionType="default", value=4))
    shutdown: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=False))
    omp_admin_distance_ipv4: OptionValue = Field(alias="ompAdminDistanceIpv4",
        default_factory=lambda: OptionValue(optionType="default", value=251))
    omp_admin_distance_ipv6: OptionValue = Field(alias="ompAdminDistanceIpv6",
        default_factory=lambda: OptionValue(optionType="default", value=251))
    advertisement_interval: OptionValue = Field(
        alias="advertisementInterval",
        description="Must be an integer value representing interval in seconds",
        default_factory=lambda: OptionValue(optionType="default", value=1)
    )
    graceful_restart_timer: OptionValue = Field(alias="gracefulRestartTimer",
        default_factory=lambda: OptionValue(optionType="default", value=43200))
    eor_timer: OptionValue = Field(alias="eorTimer",
        default_factory=lambda: OptionValue(optionType="default", value=300))
    holdtime: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=300))
    ignore_region_path_length: OptionValue = Field(alias="ignoreRegionPathLength",
        default_factory=lambda: OptionValue(optionType="default", value=False))
    transport_gateway: OptionValue = Field(alias="transportGateway",
        default_factory=lambda: OptionValue(optionType="default"))
    site_types_for_transport_gateway: OptionValue = Field(alias="siteTypesForTransportGateway",
        default_factory=lambda: OptionValue(optionType="default"))
    aspath_auto_translation: OptionValue = Field(alias="aspathAutoTranslation",
        default_factory=lambda: OptionValue(optionType="default", value=False))
    site_types: OptionValue = Field(alias="siteTypes",
        default_factory=lambda: OptionValue(optionType="default"))
    advertise_ipv4: AdvertiseProtocolIpv4 = Field(alias="advertiseIpv4", 
        default_factory=AdvertiseProtocolIpv4)
    advertise_ipv6: AdvertiseProtocolIpv6 = Field(alias="advertiseIpv6",
        default_factory=AdvertiseProtocolIpv6)
    model_config = ConfigDict(populate_by_name=True, exclude_none=True)

class OmpModel(BaseModel):
    name: str
    description: str
    data: OmpData = Field(default_factory=OmpData)
    model_config = ConfigDict(exclude_none=True)

class OmpBuilder:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        # Set up all fields with reasonable defaults
        self.data = {
            "gracefulRestart": OptionValue(optionType="default", value=True),
            "overlayAs": OptionValue(optionType="default"),
            "sendPathLimit": OptionValue(optionType="default", value=4),
            "ecmpLimit": OptionValue(optionType="default", value=4),
            "shutdown": OptionValue(optionType="default", value=False),
            "ompAdminDistanceIpv4": OptionValue(optionType="default", value=251),
            "ompAdminDistanceIpv6": OptionValue(optionType="default", value=251),
            "advertisementInterval": OptionValue(optionType="default", value=1),
            "gracefulRestartTimer": OptionValue(optionType="default", value=43200),
            "eorTimer": OptionValue(optionType="default", value=300),
            "holdtime": OptionValue(optionType="default", value=300),
            "ignoreRegionPathLength": OptionValue(optionType="default", value=False),
            "transportGateway": OptionValue(optionType="default"),
            "siteTypesForTransportGateway": OptionValue(optionType="default"),
            "aspathAutoTranslation": OptionValue(optionType="default", value=False),
            "siteTypes": OptionValue(optionType="default"),
            "advertiseIpv4": {
                "bgp": OptionValue(optionType="default", value=False),
                "ospf": OptionValue(optionType="default", value=False),
                "ospfv3": OptionValue(optionType="default", value=False),
                "connected": OptionValue(optionType="default", value=True),
                "static": OptionValue(optionType="default", value=True),
                "eigrp": OptionValue(optionType="default", value=False),
                "lisp": OptionValue(optionType="default", value=False),
                "isis": OptionValue(optionType="default", value=False)
            },
            "advertiseIpv6": {
                "bgp": OptionValue(optionType="default", value=False),
                "ospf": OptionValue(optionType="default", value=False),
                "connected": OptionValue(optionType="default", value=True),
                "static": OptionValue(optionType="default", value=True),
                "eigrp": OptionValue(optionType="default", value=False),
                "lisp": OptionValue(optionType="default", value=False),
                "isis": OptionValue(optionType="default", value=False)
            }
        }

    def set_path_option(self, path: str, field: str, option_type: str, value: Any):
        """
        Set an option at a given path.
        The path is a dot-separated string representing the nested structure.
        An empty, None, or "omp_root" path targets top-level fields.
        """
        path_str = str(path)
        if not path_str or path_str.lower() == 'nan' or path_str == "omp_root":
            current_level = self.data
        else:
            current_level = self.data
            parts = path_str.split('.')
            for part in parts:
                if isinstance(current_level, dict):
                    current_level = current_level.get(part)
                else:
                    raise KeyError(f"Unknown path component: '{part}' in path '{path_str}'")

                if current_level is None:
                    raise KeyError(f"Path '{path_str}' leads to a None value at component '{part}'.")
        
        target_object = current_level
        if isinstance(target_object, dict):
            if field not in target_object:
                raise KeyError(f"Field '{field}' not found in the target dictionary at path '{path_str}'.")
            
            processed_value = value
            if option_type == "variable" and value is not None:
                processed_value = f"{{{{{value}}}}}"
            
            target_object[field] = OptionValue(optionType=option_type, value=processed_value)
        else:
            raise KeyError(f"Target at path '{path_str}' is not a dictionary")

    def build(self) -> OmpModel:
        data_model = OmpData(**self.data)
        return OmpModel(
            name=self.name,
            description=self.description,
            data=data_model
        )

    def dict(self, **kwargs) -> dict:
        return self.build().model_dump(exclude_none=True, by_alias=True, **kwargs)

    def json(self, **kwargs) -> str:
        return self.build().model_dump_json(exclude_none=True, by_alias=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/omp"
