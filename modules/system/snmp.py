"""
Pydantic models and builder for SNMP configuration in Cisco SDWAN.
This module provides models and a builder for configuring system SNMP settings.
"""

from typing import Any, List, Optional, Union, Dict
from pydantic import BaseModel, Field, field_serializer, model_validator, ConfigDict


class OptionValue(BaseModel):
    """Model for option-value pairs with optionType handling."""
    optionType: str
    value: Union[str, int, bool, None] = None
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


class OidEntry(BaseModel):
    """Model for SNMP OID configuration."""
    id: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="OID identifier"
    )
    exclude: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=False),
        description="Whether to exclude this OID"
    )
    model_config = ConfigDict(extra="forbid")


class SnmpViewEntry(BaseModel):
    """Model for SNMP view configuration."""
    name: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="View name"
    )
    oid: List[OidEntry] = Field(
        default_factory=list,
        description="List of OID entries"
    )
    model_config = ConfigDict(extra="forbid")


class SnmpCommunityEntry(BaseModel):
    """Model for SNMP community configuration."""
    name: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Community name"
    )
    userLabel: Optional[OptionValue] = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="User label"
    )
    view: Optional[OptionValue] = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Associated view"
    )
    authorization: Optional[OptionValue] = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Authorization level"
    )
    model_config = ConfigDict(extra="forbid")


class SnmpGroupEntry(BaseModel):
    """Model for SNMP group configuration."""
    name: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Group name"
    )
    securityLevel: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Security level"
    )
    view: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Associated view"
    )
    model_config = ConfigDict(extra="forbid")


class SnmpUserEntry(BaseModel):
    """Model for SNMP user configuration."""
    name: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="User name"
    )
    auth: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Authentication protocol"
    )
    authPassword: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Authentication password"
    )
    priv: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Privacy protocol"
    )
    privPassword: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Privacy password"
    )
    group: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Associated group"
    )
    model_config = ConfigDict(extra="forbid")


class SnmpTargetEntry(BaseModel):
    """Model for SNMP target configuration."""
    vpnId: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="VPN ID for target"
    )
    ip: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Target IP address"
    )
    port: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Target port"
    )
    user: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Target user"
    )
    sourceInterface: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="Source interface"
    )
    model_config = ConfigDict(extra="forbid")


class SnmpDataModel(BaseModel):
    """Model for SNMP configuration data."""
    shutdown: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default", value=False),
        description="SNMP service shutdown state"
    )
    contact: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="SNMP contact information"
    )
    location: OptionValue = Field(
        default_factory=lambda: OptionValue(optionType="default"),
        description="SNMP system location"
    )
    view: List[SnmpViewEntry] = Field(
        default_factory=list,
        description="List of SNMP views"
    )
    community: List[SnmpCommunityEntry] = Field(
        default_factory=list,
        description="List of SNMP communities"
    )
    group: List[SnmpGroupEntry] = Field(
        default_factory=list,
        description="List of SNMP groups"
    )
    user: List[SnmpUserEntry] = Field(
        default_factory=list,
        description="List of SNMP users"
    )
    target: List[SnmpTargetEntry] = Field(
        default_factory=list,
        description="List of SNMP targets"
    )
    model_config = ConfigDict(extra="forbid")


class SnmpModel(BaseModel):
    """Root model for SNMP configuration."""
    name: str
    description: str
    data: SnmpDataModel = Field(default_factory=SnmpDataModel)
    model_config = ConfigDict(extra="forbid")

class SnmpBuilder:
    """Builder for SNMP Profile configuration."""
    
    def __init__(self, name: str, description: str):
        """Initialize the builder with name and description.
        
        Args:
            name: Name of the SNMP profile
            description: Description of the SNMP profile
        """
        self.name = name
        self.description = description
        self.model = SnmpModel(name=name, description=description)

    def set_path_option(self, path: str, field: str, option_type: str, value: Any) -> None:
        """
        Set an option at a given path with proper optionType handling.
        
        Args:
            path: Dot-separated path to the target (e.g., "view.0")
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
        if not path or path.lower() in ('nan', 'snmp_root', ''):
            if hasattr(current, field):
                setattr(current, field, OptionValue(optionType=option_type, value=value))
            return

        # Navigate the path
        parts = path.split('.')
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Invalid path: {path}")

        if hasattr(current, field):
            setattr(current, field, OptionValue(optionType=option_type, value=value))
        else:
            raise KeyError(f"Invalid field: {field} at path {path}")

    def add_view(self, name: tuple[str, str], oid_list: List[Dict[str, tuple[str, Any]]]) -> None:
        """Add a new SNMP view configuration.
        
        Args:
            name: Tuple of (optionType, value) for view name
            oid_list: List of dictionaries containing OID configurations
        """
        try:
            entry = SnmpViewEntry(
                name=OptionValue(optionType=name[0], value=name[1]),
                oid=[
                    OidEntry(
                        id=OptionValue(optionType=oid['id'][0], value=oid['id'][1]),
                        exclude=OptionValue(optionType=oid['exclude'][0], value=oid['exclude'][1])
                    ) for oid in oid_list
                ]
            )
            self.model.data.view.append(entry)
        except Exception as e:
            raise ValueError(f"Failed to add view entry: {e}")

    def add_community(
        self,
        name: tuple[str, str],
        userLabel: Optional[tuple[str, str]] = None,
        view: Optional[tuple[str, str]] = None,
        authorization: Optional[tuple[str, str]] = None
    ) -> None:
        """Add a new SNMP community configuration.
        
        Args:
            name: Tuple of (optionType, value) for community name
            userLabel: Optional tuple of (optionType, value) for user label
            view: Optional tuple of (optionType, value) for view
            authorization: Optional tuple of (optionType, value) for authorization
        """
        try:
            entry = SnmpCommunityEntry(
                name=OptionValue(optionType=name[0], value=name[1]),
                userLabel=OptionValue(optionType=userLabel[0], value=userLabel[1]) if userLabel else None,
                view=OptionValue(optionType=view[0], value=view[1]) if view else None,
                authorization=OptionValue(optionType=authorization[0], value=authorization[1]) if authorization else None
            )
            self.model.data.community.append(entry)
        except Exception as e:
            raise ValueError(f"Failed to add community entry: {e}")

    def add_group(
        self,
        name: tuple[str, str],
        securityLevel: tuple[str, str],
        view: tuple[str, str]
    ) -> None:
        """Add a new SNMP group configuration.
        
        Args:
            name: Tuple of (optionType, value) for group name
            securityLevel: Tuple of (optionType, value) for security level
            view: Tuple of (optionType, value) for view
        """
        try:
            entry = SnmpGroupEntry(
                name=OptionValue(optionType=name[0], value=name[1]),
                securityLevel=OptionValue(optionType=securityLevel[0], value=securityLevel[1]),
                view=OptionValue(optionType=view[0], value=view[1])
            )
            self.model.data.group.append(entry)
        except Exception as e:
            raise ValueError(f"Failed to add group entry: {e}")

    def add_user(
        self,
        name: tuple[str, str],
        auth: tuple[str, str],
        authPassword: tuple[str, str],
        priv: tuple[str, str],
        privPassword: tuple[str, str],
        group: tuple[str, str]
    ) -> None:
        """Add a new SNMP user configuration.
        
        Args:
            name: Tuple of (optionType, value) for user name
            auth: Tuple of (optionType, value) for auth protocol
            authPassword: Tuple of (optionType, value) for auth password
            priv: Tuple of (optionType, value) for privacy protocol
            privPassword: Tuple of (optionType, value) for privacy password
            group: Tuple of (optionType, value) for group
        """
        try:
            entry = SnmpUserEntry(
                name=OptionValue(optionType=name[0], value=name[1]),
                auth=OptionValue(optionType=auth[0], value=auth[1]),
                authPassword=OptionValue(optionType=authPassword[0], value=authPassword[1]),
                priv=OptionValue(optionType=priv[0], value=priv[1]),
                privPassword=OptionValue(optionType=privPassword[0], value=privPassword[1]),
                group=OptionValue(optionType=group[0], value=group[1])
            )
            self.model.data.user.append(entry)
        except Exception as e:
            raise ValueError(f"Failed to add user entry: {e}")

    def add_target(
        self,
        vpnId: tuple[str, Union[str, int]],
        ip: tuple[str, str],
        port: tuple[str, Union[str, int]],
        user: tuple[str, str],
        sourceInterface: tuple[str, str]
    ) -> None:
        """Add a new SNMP target configuration.
        
        Args:
            vpnId: Tuple of (optionType, value) for VPN ID
            ip: Tuple of (optionType, value) for IP address
            port: Tuple of (optionType, value) for port
            user: Tuple of (optionType, value) for user
            sourceInterface: Tuple of (optionType, value) for source interface
        """
        try:
            entry = SnmpTargetEntry(
                vpnId=OptionValue(optionType=vpnId[0], value=vpnId[1]),
                ip=OptionValue(optionType=ip[0], value=ip[1]),
                port=OptionValue(optionType=port[0], value=port[1]),
                user=OptionValue(optionType=user[0], value=user[1]),
                sourceInterface=OptionValue(optionType=sourceInterface[0], value=sourceInterface[1])
            )
            self.model.data.target.append(entry)
        except Exception as e:
            raise ValueError(f"Failed to add target entry: {e}")

    def build(self) -> SnmpModel:
        """Build and return the SnmpModel instance."""
        return self.model

    def dict(self, **kwargs) -> dict:
        """Return dictionary representation of the model."""
        return self.build().model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        """Return JSON representation of the model."""
        return self.build().model_dump_json(exclude_none=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        """Return the API URL for SNMP profile configuration."""
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/snmp"