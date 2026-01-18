from pydantic import BaseModel, Field, field_serializer, model_validator
from typing import List, Optional, Union
import re

# This is a utility class for handling vManager's optionType/value pairs
class OptionValue(BaseModel):
    optionType: str
    value: Optional[Union[str, int, bool]] = None

    @field_serializer("value")
    def serialize_value(self, v):
        if self.optionType == "variable" and isinstance(v, str):
            # Ensure variables are wrapped in {{...}}
            if not v.startswith("{{") and not v.endswith("}}"):
                return f"{{{{{v}}}}}"
        return v
    
    @model_validator(mode="after")
    def validate_option(self):
        if self.optionType == "default":
            pass
        elif self.optionType == "global":
            # Allow None for optional global fields
            pass
        elif self.optionType == "variable":
            if not isinstance(self.value, str):
                raise ValueError("OptionType 'variable' requires a string value.")
        return self

# --- Models for the IPv4 Route structure, corrected to match the working JSON ---

class IpAddress(BaseModel):
    ipAddress: OptionValue
    subnetMask: OptionValue

class NextHop(BaseModel):
    address: OptionValue
    distance: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=1))

class NextHopContainer(BaseModel):
    nextHop: List[NextHop] = Field(default_factory=list)
    nextHopWithTracker: List = Field(default_factory=list)

class OneOfIpRoute(BaseModel):
    # FIX #1 IS HERE: The container is present, matching the working JSON.
    nextHopContainer: NextHopContainer = Field(default_factory=NextHopContainer)

class Ipv4Route(BaseModel):
    prefix: IpAddress
    oneOfIpRoute: OneOfIpRoute = Field(default_factory=OneOfIpRoute)

# --- Main VPN Parcel Models ---

class MplsVpnRouteTarget(BaseModel):
    exportRtList: List = Field(default_factory=list)
    importRtList: List = Field(default_factory=list)

class VpnData(BaseModel):
    vpnId: OptionValue
    name: OptionValue
    ompAdminDistance: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    enableSdra: OptionValue = Field(default_factory=lambda: OptionValue(optionType="global", value=False))
    newHostMapping: List = Field(default_factory=list)
    ompAdvertiseIp4: List = Field(default_factory=list)
    ompAdvertiseIpv6: List = Field(default_factory=list)
    ipv4Route: List[Ipv4Route] = Field(default_factory=list)
    service: List = Field(default_factory=list)
    serviceRoute: List = Field(default_factory=list)
    greRoute: List = Field(default_factory=list)
    ipsecRoute: List = Field(default_factory=list)
    natPool: List = Field(default_factory=list)
    natPortForward: List = Field(default_factory=list)
    staticNat: List = Field(default_factory=list)
    nat64V4Pool: List = Field(default_factory=list)
    routeLeakFromGlobal: List = Field(default_factory=list)
    routeLeakFromService: List = Field(default_factory=list)
    routeLeakBetweenServices: List = Field(default_factory=list)
    mplsVpnIpv4RouteTarget: MplsVpnRouteTarget = Field(default_factory=MplsVpnRouteTarget)
    mplsVpnIpv6RouteTarget: MplsVpnRouteTarget = Field(default_factory=MplsVpnRouteTarget)

class VpnConfig(BaseModel):
    name: str
    description: str
    data: VpnData

# --- The Builder Class ---

class VpnBuilder:
    def __init__(self, name: str, description: str, vpn_id: int):
        vpn_name_option = OptionValue(optionType="global", value=name)
        vpn_id_option = OptionValue(optionType="global", value=vpn_id)
        vpn_data = VpnData(name=vpn_name_option, vpnId=vpn_id_option)
        self._model = VpnConfig(name=name, description=description, data=vpn_data)

    def build(self) -> VpnConfig:
        return self._model

    def set_path_option(self, path: str, field: str, option_type: str, value: any):
        target_obj = self._model.data
        
        if not path or path.lower() == 'vpn_root':
            if hasattr(target_obj, field):
                setattr(target_obj, field, OptionValue(optionType=option_type, value=value))
            else:
                raise AttributeError(f"Root object of type '{type(target_obj).__name__}' does not have attribute '{field}'")
            return

        parts = path.split('.')
        i = 0
        while i < len(parts):
            part = parts[i]
            
            if i + 1 < len(parts) and parts[i+1].isdigit():
                list_name = part
                index = int(parts[i+1])
                
                if not hasattr(target_obj, list_name):
                    raise AttributeError(f"'{type(target_obj).__name__}' object has no attribute '{list_name}'")
                
                prop = getattr(target_obj, list_name)
                if not isinstance(prop, list):
                    raise TypeError(f"Attribute '{list_name}' is not a list.")

                while len(prop) <= index:
                    if list_name == 'ipv4Route':
                        prop.append(Ipv4Route(prefix=IpAddress(ipAddress=OptionValue(optionType='global', value=''), subnetMask=OptionValue(optionType='global', value=''))))
                    elif list_name == 'nextHop':
                        prop.append(NextHop(address=OptionValue(optionType='global', value='')))
                    else:
                        raise TypeError(f"Auto-extending list of type '{list_name}' is not supported.")
                
                target_obj = prop[index]
                i += 2
            else:
                if not hasattr(target_obj, part):
                    raise AttributeError(f"'{type(target_obj).__name__}' object has no attribute '{part}'")
                target_obj = getattr(target_obj, part)
                i += 1

        if hasattr(target_obj, field):
            setattr(target_obj, field, OptionValue(optionType=option_type, value=value))
        else:
            raise AttributeError(f"Final object of type '{type(target_obj).__name__}' does not have attribute '{field}'")
        
    def dict(self) -> dict:
        # This returns the full model, which is what the API expects.
        return self._model.model_dump(exclude_none=True)

    def json(self) -> str:
        # This also returns the full model.
        return self._model.model_dump_json(indent=2, exclude_none=True)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/service/{serviceId}/lan/vpn"