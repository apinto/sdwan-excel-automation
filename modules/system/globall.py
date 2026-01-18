from typing import Optional, Any
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

class ServicesIpSettings(BaseModel):
    servicesGlobalServicesIpHttpServer: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpHttpsServer: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpFtpPassive: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpDomainLookup: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpArpProxy: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpRcmd: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpLineVty: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpCdp: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    servicesGlobalServicesIpLldp: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    servicesGlobalServicesIpSourceIntrf: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    globalOtherSettingsTcpKeepalivesIn: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    globalOtherSettingsTcpKeepalivesOut: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    globalOtherSettingsTcpSmallServers: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    globalOtherSettingsUdpSmallServers: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    globalOtherSettingsConsoleLogging: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    globalOtherSettingsIPSourceRoute: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    globalOtherSettingsVtyLineLogging: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    globalOtherSettingsSnmpIfindexPersist: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    globalOtherSettingsIgnoreBootp: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    globalSettingsNat64UdpTimeout: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=300))
    globalSettingsNat64TcpTimeout: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=3600))
    globalSettingsHttpAuthentication: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    globalSettingsSSHVersion: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    lacpSystemPriority: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    etherchannelFlowLoadBalance: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    etherchannelVlanLoadBalance: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    bgpCommunityNewFormat: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    model_config = ConfigDict(exclude_none=True)


class ServicesGlobal(BaseModel):
    services_ip: ServicesIpSettings = Field(default_factory=ServicesIpSettings)
    model_config = ConfigDict(exclude_none=True)


class GlobalData(BaseModel):
    services_global: ServicesGlobal = Field(default_factory=ServicesGlobal)
    model_config = ConfigDict(exclude_none=True)


class GlobalModel(BaseModel):
    name: str
    description: str
    data: GlobalData = Field(default_factory=GlobalData)
    model_config = ConfigDict(exclude_none=True)


class GlobalBuilder:
    def __init__(self, name: str, description: str):
        self.model = GlobalModel(name=name, description=description)

    def set_path_option(self, path: str, field: str, option_type: str, value: Any):
        """
        Set an option at a specified path within the model.
        """
        path_parts = path.split('.')
        current_level = self.model
        
        # Traverse the path to get to the parent model of the target field
        for part in path_parts:
            current_level = getattr(current_level, part)

        if option_type == "default":
            # Get the default value from the correct model's field
            default_option = current_level.model_fields[field].default_factory()
            option = OptionValue(optionType="default", value=default_option.value)
        else:
            option = OptionValue(optionType=option_type, value=value)

        setattr(current_level, field, option)

    def build(self) -> GlobalModel:
        # Deepcopy to prevent further modifications to the built model
        return copy.deepcopy(self.model)

    def json(self, **kwargs) -> str:
        return self.build().model_dump_json(exclude_none=True, **kwargs)

    def dict(self, **kwargs) -> dict:
        return self.build().model_dump(exclude_none=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/global"


'''
# Example usage of the GlobalBuilder to create a global services configuration

from modules.sys_profiles.pf_global import GlobalBuilder

# Initialize builder with required fields
builder = GlobalBuilder(name="test", description="test")

# Override some default options with 'global' or 'variable'
builder.set_path_option("services_ip", "servicesGlobalServicesIpHttpServer", "global", True)         # Boolean
builder.set_path_option("services_ip", "globalSettingsNat64UdpTimeout", "global", 600)              # Integer
builder.set_path_option("services_ip", "servicesGlobalServicesIpCdp", "variable", "cdp_enabled")     # Will render: "{{ cdp_enabled }}"

# You can skip any fields you want to keep with default behavior

# Build the final Pydantic model
model = builder.build()

# Output the resulting JSON
print(model.model_dump_json(indent=2, exclude_none=True))

#########################################################################################

example jason output:

{
  "name": "global",
  "description": "global",
  "data": {
    "services_global": {
      "services_ip": {
        "servicesGlobalServicesIpHttpServer": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpHttpsServer": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpFtpPassive": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpDomainLookup": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpArpProxy": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpRcmd": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpLineVty": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpCdp": {
          "optionType": "default",
          "value": false
        },
        "servicesGlobalServicesIpLldp": {
          "optionType": "default",
          "value": true
        },
        "servicesGlobalServicesIpSourceIntrf": {
          "optionType": "default"
        },
        "globalOtherSettingsTcpKeepalivesIn": {
          "optionType": "default",
          "value": true
        },
        "globalOtherSettingsTcpKeepalivesOut": {
          "optionType": "default",
          "value": true
        },
        "globalOtherSettingsTcpSmallServers": {
          "optionType": "default",
          "value": false
        },
        "globalOtherSettingsUdpSmallServers": {
          "optionType": "default",
          "value": false
        },
        "globalOtherSettingsConsoleLogging": {
          "optionType": "default",
          "value": true
        },
        "globalOtherSettingsIPSourceRoute": {
          "optionType": "default",
          "value": false
        },
        "globalOtherSettingsVtyLineLogging": {
          "optionType": "default",
          "value": false
        },
        "globalOtherSettingsSnmpIfindexPersist": {
          "optionType": "default",
          "value": true
        },
        "globalOtherSettingsIgnoreBootp": {
          "optionType": "default",
          "value": true
        },
        "globalSettingsNat64UdpTimeout": {
          "optionType": "default",
          "value": 300
        },
        "globalSettingsNat64TcpTimeout": {
          "optionType": "default",
          "value": 3600
        },
        "globalSettingsHttpAuthentication": {
          "optionType": "default"
        },
        "globalSettingsSSHVersion": {
          "optionType": "default"
        },
        "lacpSystemPriority": {
          "optionType": "default"
        },
        "etherchannelFlowLoadBalance": {
          "optionType": "default"
        },
        "etherchannelVlanLoadBalance": {
          "optionType": "default",
          "value": false
        },
        "bgpCommunityNewFormat": {
          "optionType": "defaul",
          "value": false
        }
      }
    }
  }
}


'''