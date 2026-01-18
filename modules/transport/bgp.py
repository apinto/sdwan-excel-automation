from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_serializer, model_validator
import json
import re

# Per requirements.md, this class should be self-contained within each module
# that needs it. However, to avoid circular dependencies if other modules need it,
# it's defined here. If it needs to be moved to a shared location, that's a future refactor.
class OptionValue(BaseModel):
    optionType: str
    value: Union[str, int, bool, None] = None

    @field_serializer("value")
    def serialize_value(self, v):
        if self.optionType == "variable" and isinstance(v, str):
            v = v.strip()
            if not (v.startswith("{{") and v.endswith("}}")):
                return f"{{{{{v}}}}}"
        return v

    @model_validator(mode="after")
    def validate_option(self):
        if self.optionType == "default":
            # For default, the value from the model's default_factory will be used.
            # The parser should not pass a value.
            pass
        elif self.optionType == "global":
            if self.value is None:
                # Allow None for fields that are truly optional even with 'global'
                pass
        elif self.optionType == "variable":
            if not isinstance(self.value, str):
                raise ValueError("OptionType 'variable' requires a string value.")
        return self

    class Config:
        extra = "forbid"


class MaxPrefixConfig(BaseModel):
    policyType: OptionValue = Field(default_factory=lambda: OptionValue(optionType="global", value="off"))

    class Config:
        extra = "forbid"


class AddressFamily(BaseModel):
    familyType: OptionValue = Field(default_factory=lambda: OptionValue(optionType="global", value="ipv4-unicast"))
    inRoutePolicy: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    outRoutePolicy: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    maxPrefixConfig: MaxPrefixConfig = Field(default_factory=MaxPrefixConfig)

    class Config:
        extra = "forbid"


class BGPNeighbor(BaseModel):
    address: OptionValue = Field(default_factory=lambda: OptionValue(optionType="variable", value=""))
    description: OptionValue = Field(default_factory=lambda: OptionValue(optionType="variable", value=""))
    remoteAs: OptionValue = Field(default_factory=lambda: OptionValue(optionType="variable", value=""))
    ebgpMultihop: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=1))
    keepalive: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=60))
    ifName: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    asNumber: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    sendLabel: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    password: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    nextHopSelf: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    localAs: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    sendExtCommunity: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    holdtime: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=180))
    asOverride: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    addressFamily: List[AddressFamily] = Field(default_factory=list)
    shutdown: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    sendLabelExplicit: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    sendCommunity: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))

    class Config:
        extra = "forbid"


class RedistributeProtocol(BaseModel):
    protocol: OptionValue = Field(default_factory=lambda: OptionValue(optionType="variable", value=""))
    metric: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))

    class Config:
        extra = "forbid"


class BGPAddressFamily(BaseModel):
    filter: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    originate: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    redistribute: List[RedistributeProtocol] = Field(default_factory=list)
    paths: OptionValue = Field(default_factory=lambda: OptionValue(optionType="global", value=2))
    name: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    aggregateAddress: List[Any] = Field(default_factory=list)
    network: List[Any] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class BGPData(BaseModel):
    internal: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=200))
    missingAsWorst: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    keepalive: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=60))
    compareRouterId: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    deterministic: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    neighbor: List[BGPNeighbor] = Field(default_factory=list)
    local: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=20))
    alwaysCompare: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    multipathRelax: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    external: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=20))
    routerId: OptionValue = Field(default_factory=lambda: OptionValue(optionType="variable", value=""))
    ipv6Neighbor: List[Any] = Field(default_factory=list)
    asNum: OptionValue = Field(default_factory=lambda: OptionValue(optionType="variable", value=""))
    propagateCommunity: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    holdtime: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=180))
    addressFamily: BGPAddressFamily = Field(default_factory=BGPAddressFamily)
    propagateAspath: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))

    class Config:
        extra = "forbid"


class BGPConfig(BaseModel):
    name: str
    description: str
    data: BGPData

    class Config:
        extra = "forbid"


class BGPBuilder:
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        # The data attribute will be built up and then used to instantiate BGPData
        self.data = BGPData().model_dump(exclude_none=True)

    def set_path_option(self, path: str, field: str, option_type: str, value: Any):
        """
        Set an option at a given path.
        The path is a dot-separated string representing the nested structure.
        An empty, None, or "bgp_root" path targets top-level fields.
        Handles list indexing like 'neighbor[0]'.
        """
        # Per requirement #8, if optionType is 'default', we do nothing.
        if option_type == 'default':
            return

        path_str = str(path) if path is not None else ""
        if path_str.lower() in ['nan', 'bgp_root']:
            path_str = ""

        current_level = self.data
        if path_str:
            parts = path_str.split('.')
            for part in parts:
                match = re.match(r'(\w+)\[(\d+)\]', part)
                if match:
                    key, index_str = match.groups()
                    index = int(index_str)
                    if key in current_level and isinstance(current_level[key], list):
                        if index < len(current_level[key]):
                            current_level = current_level[key][index]
                        else:
                            raise IndexError(f"Index {index} out of bounds for list '{key}' in path '{path_str}'")
                    else:
                        raise KeyError(f"List component '{key}' not found in path '{path_str}'")
                else:
                    current_level = current_level.get(part)

                if current_level is None:
                    raise ValueError(f"Path '{path_str}' leads to a None value at component '{part}'")
        
        # Now set the field in the target object (which is a dict)
        if field not in current_level:
             raise KeyError(f"Field '{field}' not found at path '{path_str}'")

        current_level[field] = {"optionType": option_type, "value": value}
        return self

    def add_neighbor(self) -> int:
        """Adds a new neighbor and returns its index."""
        new_neighbor = BGPNeighbor()
        self.data['neighbor'].append(new_neighbor.model_dump(exclude_none=True))
        return len(self.data['neighbor']) - 1

    def add_redistribute_protocol(self) -> int:
        """Adds a new redistribute protocol and returns its index."""
        new_redistribute = RedistributeProtocol()
        self.data['addressFamily']['redistribute'].append(new_redistribute.model_dump(exclude_none=True))
        return len(self.data['addressFamily']['redistribute']) - 1

    def add_address_family_to_neighbor(self, neighbor_index: int) -> int:
        """Adds a new address family to a specific neighbor and returns its index."""
        if not (0 <= neighbor_index < len(self.data['neighbor'])):
            raise IndexError(f"Neighbor index {neighbor_index} is out of bounds.")
        
        neighbor = self.data['neighbor'][neighbor_index]
        new_address_family = AddressFamily()
        neighbor['addressFamily'].append(new_address_family.model_dump(exclude_none=True))
        return len(neighbor['addressFamily']) - 1

    def build(self) -> BGPConfig:
        """Build the final BGPConfig model from the builder's state."""
        # The self.data dictionary is now ready to be loaded into the Pydantic models
        bgp_data_model = BGPData(**self.data)
        return BGPConfig(
            name=self.name,
            description=self.description,
            data=bgp_data_model
        )

    def dict(self, **kwargs) -> Dict:
        """Return the configuration as a dictionary."""
        return self.build().model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        """Return the configuration as a JSON string."""
        # Pydantic's model_dump_json will handle serialization correctly
        return self.build().model_dump_json(exclude_none=True, **kwargs)

    @staticmethod
    def create_api_url() -> str:
        """Return the API endpoint for this configuration."""
        return "/dataservice/v1/feature-profile/sdwan/transport/{transportId}/routing/bgp"

    @staticmethod
    def associate_api_url() -> str:
        """Return the API endpoint for this configuration."""
        return "/dataservice/v1/feature-profile/sdwan/transport/{transportId}/wan/vpn/{vpnId}/routing/bgp"
