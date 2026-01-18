from pydantic import BaseModel, Field, field_serializer, model_validator, ConfigDict
from typing import List, Any, Optional, Union, TypeVar, Generic
import re

# =================================================================
# Reusable Base Models (Aligned with vpn.py for consistency)
# =================================================================

T = TypeVar('T', bound=Any)

class OptionValue(BaseModel, Generic[T]):
    optionType: str
    value: Optional[Union[T, str]] = None
    model_config = ConfigDict(coerce_numbers_to_str=True)

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
            pass
        elif self.optionType == "variable":
            if not isinstance(self.value, str):
                raise ValueError("OptionType 'variable' requires a string value.")
        return self

# =================================================================
# Nested Data Models for InterfaceData
# =================================================================

class AclQos(BaseModel):
    shapingRate: OptionValue[int] = Field(default_factory=lambda: OptionValue[int](optionType="default"))

class Advanced(BaseModel):
    macAddress: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    autonegotiate: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="default"))
    icmpRedirectDisable: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    xconnect: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    tcpMss: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default"))
    ipDirectedBroadcast: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    duplex: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    arpTimeout: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default", value=1200))
    mediaType: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    ipMtu: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default", value=1500))
    speed: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    loadInterval: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default", value=30))

class Vrrp(BaseModel):
    timer: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default", value=1000))
    tlocPrefChangeValue: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default"))
    trackingObject: List = Field(default_factory=list)
    group_id: OptionValue[Union[int, str]]
    tlocPrefChange: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    ipAddress: OptionValue[str]
    minPreemptDelay: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default"))
    priority: OptionValue[Union[int, str]]
    trackOmp: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    ipAddressSecondary: List = Field(default_factory=list)

class NatPool(BaseModel):
    prefixLength: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default"))
    rangeStart: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    overload: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="global", value=True))
    rangeEnd: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))

class NatAttributesIpv4(BaseModel):
    natPool: NatPool = Field(default_factory=NatPool)
    natType: OptionValue[str]
    natLoopback: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    udpTimeout: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="global", value=1))
    tcpTimeout: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="global", value=60))
    newStaticNat: List = Field(default_factory=list)

class StaticIpV4AddressPrimary(BaseModel):
    ipAddress: OptionValue[str]
    subnetMask: OptionValue[str]

class Static(BaseModel):
    staticIpV4AddressPrimary: Optional[StaticIpV4AddressPrimary] = None
    staticIpV4AddressSecondary: List = Field(default_factory=list)

class IntfIpAddress(BaseModel):
    static: Static = Field(default_factory=Static)

class Trustsec(BaseModel):
    propogate: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="global", value=True))
    securityGroupTag: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default"))
    enableEnforcedPropogation: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="default"))
    enforcedSecurityGroupTag: OptionValue[int] = Field(default_factory=lambda: OptionValue(optionType="default"))
    enableSGTPropogation: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="global", value=False))

# =================================================================
# Main Data and Config Models
# =================================================================

class InterfaceData(BaseModel):
    nat: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="global", value=False))
    aclQos: AclQos = Field(default_factory=AclQos)
    portChannelInterface: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="global", value=False))
    advanced: Advanced = Field(default_factory=Advanced)
    vrrpIpv6: List = Field(default_factory=list)
    description: OptionValue[str]
    vrrp: List[Vrrp] = Field(default_factory=list)
    natAttributesIpv4: Optional[NatAttributesIpv4] = None
    natIpv6: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="global", value=False))
    dhcpHelper: OptionValue[str] = Field(default_factory=lambda: OptionValue(optionType="default"))
    intfIpAddress: IntfIpAddress = Field(default_factory=IntfIpAddress)
    trustsec: Trustsec = Field(default_factory=Trustsec)
    interfaceName: OptionValue[str]
    shutdown: OptionValue[bool] = Field(default_factory=lambda: OptionValue(optionType="global", value=False))
    arp: List = Field(default_factory=list)

class ServiceInterfaceConfig(BaseModel):
    name: str
    description: str
    data: InterfaceData

# =================================================================
# Builder Class
# =================================================================

class ServiceInterfaceBuilder:
    def __init__(self, name: str, description: str):
        self.name = name
        self._model = ServiceInterfaceConfig(
            name=name,
            description=description,
            data=InterfaceData(
                interfaceName=OptionValue[str](optionType="global", value=""),
                description=OptionValue[str](optionType="global", value=description)
            )
        )

    def set_path_option(self, path: str, value: Any, option_type: str = "global"):
        parts = re.split(r'\.(?!\d)', path)
        current_level = self._model.data
        final_key = parts.pop()

        for part in parts:
            list_match = re.match(r'(\w+)\[(\d+)\]', part) or re.match(r'(\w+)\.(\d+)', part)
            
            if list_match:
                list_name, index = list_match.groups()
                index = int(index)
                target_list = getattr(current_level, list_name)
                
                while len(target_list) <= index:
                    item_type = current_level.model_fields[list_name].annotation.__args__[0]
                    if item_type is Vrrp:
                        new_item = item_type(
                            group_id=OptionValue[int](optionType='global', value=0),
                            ipAddress=OptionValue[str](optionType='global', value=''),
                            priority=OptionValue[int](optionType='global', value=0)
                        )
                    else:
                        try:
                            new_item = item_type()
                        except TypeError:
                            raise TypeError(f"Auto-instantiation for list item type {item_type.__name__} failed.")
                    target_list.append(new_item)
                current_level = target_list[index]
            else:
                next_level = getattr(current_level, part, None)
                if next_level is None:
                    field_type = current_level.model_fields[part].annotation
                    if hasattr(field_type, '__origin__') and type(None) in getattr(field_type, '__args__', []):
                        field_type = field_type.__args__[0]
                    
                    if hasattr(field_type, 'model_fields'):
                        if field_type is NatAttributesIpv4:
                            new_instance = field_type(natType=OptionValue[str](optionType='global', value=''))
                        elif field_type is StaticIpV4AddressPrimary:
                            new_instance = field_type(
                                ipAddress=OptionValue[str](optionType='global', value=''),
                                subnetMask=OptionValue[str](optionType='global', value='')
                            )
                        else:
                            try:
                                new_instance = field_type()
                            except TypeError:
                                raise TypeError(f"Auto-instantiation for model type {field_type.__name__} failed.")
                        setattr(current_level, part, new_instance)
                        current_level = new_instance
                    else:
                        raise AttributeError(f"Path component '{part}' does not exist.")
                else:
                    current_level = next_level

        final_field = current_level.model_fields.get(final_key)
        if not final_field:
            raise AttributeError(f"'{type(current_level).__name__}' has no attribute '{final_key}'")

        # This is the key change: we instantiate the specific OptionValue[T] type
        # The type T is extracted from the field's annotation, e.g., OptionValue[bool] -> bool
        option_value_type = final_field.annotation
        setattr(current_level, final_key, option_value_type(value=value, optionType=option_type))
            
        return self

    def build(self) -> ServiceInterfaceConfig:
        return self._model

    def dict(self) -> dict:
        return self._model.model_dump(by_alias=True, exclude_none=True)

    def json(self) -> str:
        return self._model.model_dump_json(by_alias=True, exclude_none=True, indent=2)

    @staticmethod
    def api_url(serviceId: str, vpnId: str) -> str:
        return f"/dataservice/v1/feature-profile/sdwan/service/{serviceId}/lan/vpn/{vpnId}/interface/ethernet"
