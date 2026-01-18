"""
Pydantic models and builder for Logging configuration in Cisco SDWAN.
This module provides models and a builder for configuring system logging settings.
"""

from typing import Any, List, Optional, Union, Dict
from pydantic import BaseModel, Field, field_serializer, ConfigDict, model_validator


class OptionValue(BaseModel):
    """Model for option-value pairs with optionType handling."""
    optionType: str
    value: Union[str, int, bool, List[str], None] = None
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


class DiskFileModel(BaseModel):
    """Model for disk file logging settings."""
    diskFileSize: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=10),
        description="Size of disk log file in MB"
    )
    diskFileRotate: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=10),
        description="Number of rotated log files to keep"
    )
    model_config = ConfigDict(extra="forbid")


class DiskModel(BaseModel):
    """Model for disk logging configuration."""
    file: DiskFileModel = Field(default_factory=DiskFileModel)
    model_config = ConfigDict(extra="forbid")


class TlsProfileEntry(BaseModel):
    """Model for TLS profile configuration."""
    profile: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="TLS profile name"
    )
    tlsVersion: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="TLS version to use"
    )
    authType: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Authentication type"
    )
    cipherSuiteList: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=[]),
        description="List of cipher suites"
    )
    model_config = ConfigDict(extra="forbid")


class ServerEntry(BaseModel):
    """Model for logging server configuration."""
    name: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Server name or IP address"
    )
    vpn: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="VPN ID for server"
    )
    sourceInterface: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Source interface for logging"
    )
    priority: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value="informational"),
        description="Log message priority"
    )
    tlsEnable: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=False),
        description="Enable TLS for server connection"
    )
    model_config = ConfigDict(extra="forbid")


class LoggDataModel(BaseModel):
    """Model for logging configuration data."""
    disk: DiskModel = Field(
        default_factory=DiskModel,
        description="Disk logging configuration"
    )
    tlsProfile: List[TlsProfileEntry] = Field(
        default_factory=list,
        description="List of TLS profiles"
    )
    server: List[ServerEntry] = Field(
        default_factory=list,
        description="List of logging servers"
    )
    ipv6Server: List[Any] = Field(
        default_factory=list,
        description="List of IPv6 logging servers"
    )
    model_config = ConfigDict(extra="forbid")


class LoggModel(BaseModel):
    """Root model for logging configuration."""
    name: str
    description: str
    data: LoggDataModel = Field(default_factory=LoggDataModel)
    model_config = ConfigDict(extra="forbid")

class LoggBuilder:
    """Builder for Logging Profile configuration."""
    
    def __init__(self, name: str, description: str):
        """Initialize the builder with name and description.
        
        Args:
            name: Name of the logging profile
            description: Description of the logging profile
        """
        self.name = name
        self.description = description
        self.model = LoggModel(name=name, description=description)

    def set_path_option(self, path: str, field: str, option_type: str, value: Any) -> None:
        """
        Set an option at a given path with proper optionType handling.
        
        Args:
            path: Dot-separated path to the target (e.g., "disk.file", "tlsProfile.0")
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
        current = self.model.data

        # Handle empty or None path
        if not path or path.lower() in ('nan', 'logg_root', ''):
            if hasattr(current, field):
                setattr(current, field, OptionValue(optionType=option_type, value=value))
            return

        # Navigate the path
        parts = path.split('.')
        for part in parts:
            if part == "file":  # Handle disk file special case
                current = current.disk.file
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Invalid path: {path}")

        # Set the value on the final object
        if hasattr(current, field):
            setattr(current, field, OptionValue(optionType=option_type, value=value))
        else:
            raise KeyError(f"Invalid field: {field} at path {path}")

    def add_tls_profile(
        self,
        profile: tuple[str, str],
        tls_version: tuple[str, str],
        auth_type: tuple[str, str],
        cipher_suite_list: tuple[str, List[str]],
    ) -> None:
        """Add a new TLS profile configuration.
        
        Args:
            profile: Tuple of (optionType, value) for profile name
            tls_version: Tuple of (optionType, value) for TLS version
            auth_type: Tuple of (optionType, value) for authentication type
            cipher_suite_list: Tuple of (optionType, value) for cipher suites
        """
        entry = TlsProfileEntry(
            profile=OptionValue(optionType=profile[0], value=profile[1]),
            tlsVersion=OptionValue(optionType=tls_version[0], value=tls_version[1]),
            authType=OptionValue(optionType=auth_type[0], value=auth_type[1]),
            cipherSuiteList=OptionValue(optionType=cipher_suite_list[0], value=cipher_suite_list[1]),
        )
        self.model.data.tlsProfile.append(entry)

    def add_server(
        self,
        name: tuple[str, str],
        vpn: tuple[str, int],
        source_interface: tuple[str, Optional[str]] = ("default", None),
        priority: tuple[str, str] = ("default", "informational"),
        tls_enable: tuple[str, bool] = ("default", False),
    ) -> None:
        """Add a new logging server configuration.
        
        Args:
            name: Tuple of (optionType, value) for server name/IP
            vpn: Tuple of (optionType, value) for VPN ID
            source_interface: Tuple of (optionType, value) for source interface
            priority: Tuple of (optionType, value) for log priority
            tls_enable: Tuple of (optionType, value) for TLS enablement
        """
        entry = ServerEntry(
            name=OptionValue(optionType=name[0], value=name[1]),
            vpn=OptionValue(optionType=vpn[0], value=vpn[1]),
            sourceInterface=OptionValue(optionType=source_interface[0], value=source_interface[1]),
            priority=OptionValue(optionType=priority[0], value=priority[1]),
            tlsEnable=OptionValue(optionType=tls_enable[0], value=tls_enable[1]),
        )
        self.model.data.server.append(entry)

    def set_disk_file_options(self, disk_file_size: tuple[str, int], disk_file_rotate: tuple[str, int]) -> None:
        """Set disk file logging options.
        
        Args:
            disk_file_size: Tuple of (optionType, value) for file size in MB
            disk_file_rotate: Tuple of (optionType, value) for number of files to keep
        """
        self.model.data.disk.file.diskFileSize = OptionValue(
            optionType=disk_file_size[0], 
            value=disk_file_size[1]
        )
        self.model.data.disk.file.diskFileRotate = OptionValue(
            optionType=disk_file_rotate[0], 
            value=disk_file_rotate[1]
        )

    def build(self) -> LoggModel:
        """Build and return the LoggModel instance."""
        return self.model

    def dict(self, **kwargs) -> dict:
        """Return dictionary representation of the model."""
        return self.build().model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        """Return JSON representation of the model."""
        return self.build().model_dump_json(exclude_none=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        """Return the API URL for logging profile configuration."""
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/logging"