from typing import Any, List, Optional, Dict, Union
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

class StaticIpV4AddressPrimary(BaseModel):
    ipAddress: OptionValue
    subnetMask: OptionValue

class Static(BaseModel):
    staticIpV4AddressPrimary: StaticIpV4AddressPrimary
    staticIpV4AddressSecondary: List[Any] = Field(default_factory=list)

class IntfIpAddress(BaseModel):
    static: Static

class AllowService(BaseModel):
    all: OptionValue
    bfd: OptionValue
    dns: OptionValue
    ssh: OptionValue
    bgp: OptionValue
    ntp: OptionValue
    snmp: OptionValue
    icmp: OptionValue
    stun: OptionValue
    ospf: OptionValue
    netconf: OptionValue
    https: OptionValue
    dhcp: OptionValue

class Tunnel(BaseModel):
    border: OptionValue
    natRefreshInterval: OptionValue
    color: OptionValue
    tunnelTcpMss: OptionValue
    lastResortCircuit: OptionValue
    maxControlConnections: OptionValue
    vBondAsStunServer: OptionValue
    excludeControllerGroupList: OptionValue
    portHop: OptionValue
    setSdwanTunnelMTUToMax: OptionValue
    restrict: OptionValue
    lowBandwidthLink: OptionValue
    helloTolerance: OptionValue
    ctsSgtPropagation: OptionValue
    carrier: OptionValue
    bind: OptionValue
    tlocExtensionGreTo: OptionValue
    vManageConnectionPreference: OptionValue
    perTunnelQos: OptionValue
    networkBroadcast: OptionValue
    helloInterval: OptionValue
    clearDontFragment: OptionValue
    allowFragmentation: OptionValue
    group: OptionValue

class TlocExtensionGreFrom(BaseModel):
    xconnect: OptionValue
    sourceIp: OptionValue

class Advanced(BaseModel):
    autonegotiate: OptionValue
    tlocExtension: OptionValue
    icmpRedirectDisable: OptionValue
    tlocExtensionGreFrom: TlocExtensionGreFrom
    duplex: OptionValue
    mediaType: OptionValue
    speed: OptionValue
    loadInterval: OptionValue
    macAddress: OptionValue
    tcpMss: OptionValue
    ipDirectedBroadcast: OptionValue
    intrfMtu: OptionValue
    arpTimeout: OptionValue
    ipMtu: OptionValue

class MultiRegionFabric(BaseModel):
    secondaryRegion: OptionValue
    coreRegion: OptionValue
    enableCoreRegion: OptionValue
    enableSecondaryRegion: OptionValue

class AclQos(BaseModel):
    shapingRate: OptionValue
    adaptiveQoS: OptionValue

class EncapsulationEntry(BaseModel):
    preference: OptionValue
    weight: OptionValue
    encap: OptionValue

class DataModel(BaseModel):
    nat: OptionValue
    aclQos: AclQos
    encapsulation: List[EncapsulationEntry]
    portChannelInterface: OptionValue
    multiRegionFabric: MultiRegionFabric
    advanced: Advanced
    description: OptionValue
    autoDetectBandwidth: OptionValue
    natIpv6: OptionValue
    bandwidthDownstream: OptionValue
    bandwidthUpstream: OptionValue
    dhcpHelper: OptionValue
    allowService: AllowService
    intfIpAddress: IntfIpAddress
    serviceProvider: OptionValue
    tunnelInterface: OptionValue
    interfaceName: OptionValue
    arp: List[Any] = Field(default_factory=list)
    shutdown: OptionValue
    tunnel: Tunnel
    blockNonSourceIp: OptionValue

class TransportIntfModel(BaseModel):
    name: str
    description: str
    data: DataModel


class InterfaceBuilder:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        # Set up all fields with reasonable defaults or empty structures
        self.data = {
            "nat": OptionValue(optionType="default", value=False),
            "aclQos": AclQos(
                shapingRate=OptionValue(optionType="default"),
                adaptiveQoS=OptionValue(optionType="default", value=False)
            ),
            "encapsulation": [],
            "portChannelInterface": OptionValue(optionType="default", value=False),
            "multiRegionFabric": MultiRegionFabric(
                secondaryRegion=OptionValue(optionType="default", value="secondary-shared"),
                coreRegion=OptionValue(optionType="default", value="core-shared"),
                enableCoreRegion=OptionValue(optionType="default", value=False),
                enableSecondaryRegion=OptionValue(optionType="default", value=False)
            ),
            "advanced": Advanced(
                autonegotiate=OptionValue(optionType="default"),
                tlocExtension=OptionValue(optionType="default"),
                icmpRedirectDisable=OptionValue(optionType="default", value=True),
                tlocExtensionGreFrom=TlocExtensionGreFrom(
                    xconnect=OptionValue(optionType="default"),
                    sourceIp=OptionValue(optionType="default")
                ),
                duplex=OptionValue(optionType="default"),
                mediaType=OptionValue(optionType="default"),
                speed=OptionValue(optionType="default"),
                loadInterval=OptionValue(optionType="default", value=30),
                macAddress=OptionValue(optionType="default"),
                tcpMss=OptionValue(optionType="default"),
                ipDirectedBroadcast=OptionValue(optionType="default", value=False),
                intrfMtu=OptionValue(optionType="default", value=1500),
                arpTimeout=OptionValue(optionType="default", value=1200),
                ipMtu=OptionValue(optionType="default", value=1500)
            ),
            "description": OptionValue(optionType="global", value=name),
            "autoDetectBandwidth": OptionValue(optionType="default", value=False),
            "natIpv6": OptionValue(optionType="default", value=False),
            "bandwidthDownstream": OptionValue(optionType="default"),
            "bandwidthUpstream": OptionValue(optionType="default"),
            "dhcpHelper": OptionValue(optionType="default"),
            "allowService": AllowService(
                all=OptionValue(optionType="default", value=False),
                bfd=OptionValue(optionType="default", value=False),
                dns=OptionValue(optionType="default", value=True),
                ssh=OptionValue(optionType="default", value=False),
                bgp=OptionValue(optionType="global", value=False),
                ntp=OptionValue(optionType="default", value=False),
                snmp=OptionValue(optionType="default", value=False),
                icmp=OptionValue(optionType="default", value=True),
                stun=OptionValue(optionType="default", value=False),
                ospf=OptionValue(optionType="default", value=False),
                netconf=OptionValue(optionType="default", value=False),
                https=OptionValue(optionType="default", value=True),
                dhcp=OptionValue(optionType="default", value=True)
            ),
            "intfIpAddress": IntfIpAddress(
                static=Static(
                    staticIpV4AddressPrimary=StaticIpV4AddressPrimary(
                        ipAddress=OptionValue(optionType="variable", value="{{wEthInt_2_ipv4Addr_stat_prim_ipAddr}}"),
                        subnetMask=OptionValue(optionType="variable", value="{{wEthInt_2_ipv4Addr_stat_prim_subnMask}}")
                    ),
                    staticIpV4AddressSecondary=[]
                )
            ),
            "serviceProvider": OptionValue(optionType="default"),
            "tunnelInterface": OptionValue(optionType="global", value=True),
            "interfaceName": OptionValue(optionType="global", value="GigabitEthernet3"),
            "arp": [],
            "shutdown": OptionValue(optionType="global", value=False),
            "tunnel": Tunnel(
                border=OptionValue(optionType="default", value=False),
                natRefreshInterval=OptionValue(optionType="default", value=5),
                color=OptionValue(optionType="variable", value="{{wEthInt_2_tunnel_color}}"),
                tunnelTcpMss=OptionValue(optionType="default"),
                lastResortCircuit=OptionValue(optionType="default", value=False),
                maxControlConnections=OptionValue(optionType="default"),
                vBondAsStunServer=OptionValue(optionType="default", value=False),
                excludeControllerGroupList=OptionValue(optionType="default"),
                portHop=OptionValue(optionType="default", value=True),
                setSdwanTunnelMTUToMax=OptionValue(optionType="default", value=False),
                restrict=OptionValue(optionType="default", value=False),
                lowBandwidthLink=OptionValue(optionType="default", value=False),
                helloTolerance=OptionValue(optionType="default", value=12),
                ctsSgtPropagation=OptionValue(optionType="default", value=False),
                carrier=OptionValue(optionType="default", value="default"),
                bind=OptionValue(optionType="default"),
                tlocExtensionGreTo=OptionValue(optionType="default"),
                vManageConnectionPreference=OptionValue(optionType="default", value=5),
                perTunnelQos=OptionValue(optionType="default", value=False),
                networkBroadcast=OptionValue(optionType="default", value=False),
                helloInterval=OptionValue(optionType="default", value=1000),
                clearDontFragment=OptionValue(optionType="default", value=False),
                allowFragmentation=OptionValue(optionType="default", value=False),
                group=OptionValue(optionType="global", value=100)
            ),
            "blockNonSourceIp": OptionValue(optionType="default", value=False)
        }

    def set_path_option(self, path: str, field: str, option_type: str, value: Any):
        """
        Set an option at a given path.
        The path is a dot-separated string representing the nested structure.
        An empty, None, or "interface_root" path targets top-level fields.
        """
        # Handle NaN path from pandas as root
        path_str = str(path)
        if not path_str or path_str.lower() == 'nan' or path_str == "interface_root":
            current_level = self.data
        else:
            current_level = self.data
            parts = path_str.split('.')
            for part in parts:
                if isinstance(current_level, dict):
                    current_level = current_level.get(part)
                elif hasattr(current_level, part):
                    current_level = getattr(current_level, part)
                else:
                    raise KeyError(f"Unknown path component: '{part}' in path '{path_str}'")

                if current_level is None:
                    raise KeyError(f"Path '{path_str}' leads to a None value at component '{part}'.")
        
        target_object = current_level
        if isinstance(target_object, dict):
            if field not in target_object:
                raise KeyError(f"Field '{field}' not found in the target dictionary at path '{path_str}'.")
            
            if isinstance(target_object[field], OptionValue):
                target_object[field] = OptionValue(optionType=option_type, value=value)
            else:
                # This case is for when the field is a Pydantic model itself
                # We assume the user wants to set a field *within* that model
                # This part of the logic might need refinement if the use case is different
                nested_model = target_object[field]
                if hasattr(nested_model, field):
                    setattr(nested_model, field, OptionValue(optionType=option_type, value=value))
                else:
                    raise TypeError(f"Field '{field}' at path '{path_str}' is complex and not an OptionValue.")

        elif hasattr(target_object, field):
            if isinstance(getattr(target_object, field), OptionValue):
                setattr(target_object, field, OptionValue(optionType=option_type, value=value))
            else:
                raise TypeError(f"Field '{field}' at path '{path_str}' is not an OptionValue field.")
        else:
            raise KeyError(f"Field '{field}' not found at path '{path_str}'")

    def add_encapsulation(self, preference: tuple[str, Any], weight: tuple[str, Any], encap: tuple[str, Any]):
        entry = EncapsulationEntry(
            preference=OptionValue(optionType=preference[0], value=preference[1]),
            weight=OptionValue(optionType=weight[0], value=weight[1]),
            encap=OptionValue(optionType=encap[0], value=encap[1])
        )
        self.data["encapsulation"].append(entry)

    def build(self) -> TransportIntfModel:
        # Check if this is a subinterface (contains a dot in the interface name)
        interface_name = self.data.get("interfaceName", None)
        if interface_name and isinstance(interface_name, OptionValue):
            interface_name_value = interface_name.value
            
            # If it's a subinterface (contains a dot), remove the intrfMtu parameter
            if isinstance(interface_name_value, str) and '.' in interface_name_value:
                # Set to None so it will be excluded in the model_dump with exclude_none=True
                if "advanced" in self.data and hasattr(self.data["advanced"], "intrfMtu"):
                    self.data["advanced"].intrfMtu = None

        # Remove all tunnel parameters if tunnelInterface is FALSE
        tunnel_interface = self.data.get("tunnelInterface", None)
        if tunnel_interface and isinstance(tunnel_interface, OptionValue):
            if tunnel_interface.value is False:
                tunnel_obj = self.data.get("tunnel", None)
                if tunnel_obj:
                    # List of all tunnel parameters to remove
                    tunnel_fields = [
                        "border", "natRefreshInterval", "color", "tunnelTcpMss", "lastResortCircuit",
                        "maxControlConnections", "vBondAsStunServer", "excludeControllerGroupList", "portHop",
                        "setSdwanTunnelMTUToMax", "restrict", "lowBandwidthLink", "helloTolerance",
                        "ctsSgtPropagation", "carrier", "bind", "tlocExtensionGreTo", "vManageConnectionPreference",
                        "perTunnelQos", "networkBroadcast", "helloInterval", "clearDontFragment",
                        "allowFragmentation", "group"
                    ]
                    for field in tunnel_fields:
                        if hasattr(tunnel_obj, field):
                            setattr(tunnel_obj, field, None)

        # Directly pass the dictionary to the DataModel constructor
        data_model = DataModel(**self.data)
        return TransportIntfModel(
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
        return "/dataservice/v1/feature-profile/sdwan/transport/{transportId}/wan/vpn/{vpnId}/interface/ethernet/"

# Example usage:
'''
builder = InterfaceBuilder(
    name="SP1",
    description=""
)
builder.set_option("nat", "default", False)
builder.set_nested_option("advanced", "icmpRedirectDisable", "default", True)
builder.add_encapsulation(
    preference=("default", None),
    weight=("default", 1),
    encap=("global", "ipsec")
)
print(builder.json(indent=2))
'''