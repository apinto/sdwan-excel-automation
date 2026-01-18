from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_serializer, ConfigDict, model_validator

class OptionValue(BaseModel):
    """Model for option-value pairs with optionType handling."""
    optionType: str
    value: Optional[Any] = None
    model_config = ConfigDict(extra="forbid")

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

class NtpServerEntry(BaseModel):
    """Model for NTP server configuration."""
    name: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    key: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    vpn: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    version: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=4))
    sourceInterface: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    prefer: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    model_config = ConfigDict(extra="forbid")

class NtpAuthenticationKeyEntry(BaseModel):
    """Model for NTP authentication key entry."""
    keyId: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    md5Value: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    model_config = ConfigDict(extra="forbid")

class NtpAuthentication(BaseModel):
    """Model for NTP authentication settings."""
    authenticationKeys: List[NtpAuthenticationKeyEntry] = Field(default_factory=list)
    trustedKeys: OptionValue = Field(default_factory=lambda: OptionValue(optionType="global", value=[]))
    model_config = ConfigDict(extra="forbid")

class NtpLeader(BaseModel):
    """Model for NTP leader settings."""
    enable: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    model_config = ConfigDict(extra="forbid")

class NtpDataModel(BaseModel):
    """Model for NTP configuration data."""
    server: List[NtpServerEntry] = Field(default_factory=list)
    authentication: NtpAuthentication = Field(default_factory=NtpAuthentication)
    leader: NtpLeader = Field(default_factory=NtpLeader)
    model_config = ConfigDict(extra="forbid")

class NtpModel(BaseModel):
    """Root model for NTP configuration."""
    name: str
    description: str
    data: NtpDataModel = Field(default_factory=NtpDataModel)
    model_config = ConfigDict(extra="forbid")

class NtpBuilder:
    """Builder for NTP Profile configuration."""
    
    def __init__(self, name: str, description: str):
        """Initialize the builder with name and description."""
        self.name = name
        self.description = description
        self.data = NtpDataModel()  # Uses default values from model

    def set_path_option(self, path: str, field: str, option_type: str, value: Any) -> None:
        """
        Set an option at a given path with proper optionType handling.
        
        Args:
            path: Dot-separated path to the target (e.g., "leader", "authentication")
            field: Field name to set
            option_type: Type of option ("default", "global", "variable")
            value: Value to set
        """
        if option_type == "default":
            return  # Ignore default values as per requirements
            
        # Handle variable type formatting
        if option_type == "variable" and isinstance(value, str):
            if not value.startswith("{{") and not value.endswith("}}"):
                value = f"{{{{{value}}}}}"
                
        # Start at the root of data
        current = self.data
        
        # Handle empty or None path
        if not path or path.lower() in ('nan', 'ntp_root', ''):
            if hasattr(current, field):
                setattr(current, field, OptionValue(optionType=option_type, value=value))
            return
            
        # Navigate the path
        parts = path.split('.')
        for part in parts[:-1]:  # All but the last part
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Invalid path: {path}")
                
        # Set the value on the final object
        last_part = parts[-1]
        if hasattr(current, last_part):
            target = getattr(current, last_part)
            if isinstance(target, OptionValue):
                setattr(current, last_part, OptionValue(optionType=option_type, value=value))
            elif hasattr(target, field):
                setattr(target, field, OptionValue(optionType=option_type, value=value))
        elif hasattr(current, field):
            setattr(current, field, OptionValue(optionType=option_type, value=value))
        else:
            raise KeyError(f"Invalid field: {field} at path {path}")

    def add_server(
        self,
        *,
        name: tuple[str, Any],
        key: tuple[str, Any],
        vpn: tuple[str, Any],
        version: tuple[str, Any],
        source_interface: tuple[str, Any],
        prefer: tuple[str, Any],
    ) -> None:
        """Add a new NTP server entry."""
        entry = NtpServerEntry(
            name=OptionValue(optionType=name[0], value=name[1]),
            key=OptionValue(optionType=key[0], value=key[1] if len(key) > 1 else None),
            vpn=OptionValue(optionType=vpn[0], value=vpn[1]),
            version=OptionValue(optionType=version[0], value=version[1]),
            sourceInterface=OptionValue(optionType=source_interface[0], value=source_interface[1] if len(source_interface) > 1 else None),
            prefer=OptionValue(optionType=prefer[0], value=prefer[1]),
        )
        self.data.server.append(entry)

    def add_authentication_key(self, keyId: tuple[str, Any], md5Value: tuple[str, Any]) -> None:
        """Add a new NTP authentication key entry."""
        entry = NtpAuthenticationKeyEntry(
            keyId=OptionValue(optionType=keyId[0], value=keyId[1]),
            md5Value=OptionValue(optionType=md5Value[0], value=md5Value[1]),
        )
        self.data.authentication.authenticationKeys.append(entry)

    def set_trusted_keys(self, option_type: str, value: Any) -> None:
        """Set the trusted keys for NTP authentication."""
        self.data.authentication.trustedKeys = OptionValue(optionType=option_type, value=value)

    def set_leader_enable(self, option_type: str, value: Any) -> None:
        """Set the NTP leader enable option."""
        self.data.leader.enable = OptionValue(optionType=option_type, value=value)

    def build(self) -> NtpModel:
        """Build and return the NtpModel instance."""
        return NtpModel(
            name=self.name,
            description=self.description,
            data=self.data
        )

    def dict(self, **kwargs) -> dict:
        """Return dictionary representation of the model."""
        return self.build().model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        """Return JSON representation of the model."""
        return self.build().model_dump_json(exclude_none=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        """Return the API URL for NTP profile configuration."""
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/ntp"

