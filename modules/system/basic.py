from typing import Any, List, Optional
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

class Clock(BaseModel):
    """Model for timezone settings."""
    timezone: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value="UTC"))
    model_config = ConfigDict(extra="forbid")

class GeoFencing(BaseModel):
    """Model for geo-fencing settings."""
    enable: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    model_config = ConfigDict(extra="forbid")

class GpsLocation(BaseModel):
    """Model for GPS location settings."""
    longitude: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    latitude: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    geoFencing: GeoFencing = Field(default_factory=GeoFencing)
    model_config = ConfigDict(extra="forbid")

class OnDemand(BaseModel):
    """Model for on-demand connection settings."""
    onDemandEnable: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    onDemandIdleTimeout: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=10))
    model_config = ConfigDict(extra="forbid")

class AffinityPerVrfEntry(BaseModel):
    """Model for VRF affinity settings."""
    affinityGroupNumber: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    vrfRange: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    model_config = ConfigDict(extra="forbid")

class BasicDataModel(BaseModel):
    """Model for basic system settings data."""
    clock: Clock = Field(default_factory=Clock)
    description: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    location: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    gpsLocation: GpsLocation = Field(default_factory=GpsLocation)
    deviceGroups: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    controllerGroupList: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    overlayId: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=1))
    portOffset: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=0))
    portHop: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    controlSessionPps: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=300))
    trackTransport: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    trackInterfaceTag: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    consoleBaudRate: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value="9600"))
    maxOmpSessions: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    multiTenant: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    trackDefaultGateway: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    trackerDiaStabilizeStatus: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    adminTechOnFailure: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=True))
    idleTimeout: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    onDemand: OnDemand = Field(default_factory=lambda: OnDemand())
    transportGateway: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    epfr: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value="disabled"))
    siteType: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    affinityGroupNumber: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    affinityGroupPreference: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default"))
    affinityPreferenceAuto: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    affinityPerVrf: List[AffinityPerVrfEntry] = Field(default_factory=list)
    
    model_config = ConfigDict(extra="forbid")

class BasicModel(BaseModel):
    """Root model for basic system configuration."""
    name: str
    description: str
    data: BasicDataModel = Field(default_factory=BasicDataModel)
    model_config = ConfigDict(extra="forbid")

    def dict(self, **kwargs) -> dict:
        """Return dictionary representation, excluding None values."""
        return self.model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        """Return JSON representation, excluding None values."""
        return self.model_dump_json(exclude_none=True, **kwargs)

class BasicBuilder:
    """Builder for Basic Profile configuration."""
    
    def __init__(self, name: str, description: str):
        """Initialize the builder with name and description."""
        self.name = name
        self.description = description
        self.data = BasicDataModel()  # Uses default values from model

    def set_path_option(self, path: str, field: str, option_type: str, value: Any) -> None:
        """
        Set an option at a given path with proper optionType handling.
        
        Args:
            path: Dot-separated path to the target (e.g., "clock", "gpsLocation.geoFencing")
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
        if not path or path.lower() in ('nan', 'basic_root', ''):
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
            
    def add_affinity_per_vrf(self, affinity_group_number: tuple[str, Any], vrf_range: tuple[str, Any]) -> None:
        """
        Add an affinity per VRF entry.
        
        Args:
            affinity_group_number: Tuple of (optionType, value) for group number
            vrf_range: Tuple of (optionType, value) for VRF range
        """
        entry = AffinityPerVrfEntry(
            affinityGroupNumber=OptionValue(optionType=affinity_group_number[0], value=affinity_group_number[1]),
            vrfRange=OptionValue(optionType=vrf_range[0], value=vrf_range[1])
        )
        self.data.affinityPerVrf.append(entry)

    def build(self) -> BasicModel:
        """Build and return the BasicModel instance."""
        return BasicModel(
            name=self.name,
            description=self.description,
            data=self.data
        )

    def dict(self, **kwargs) -> dict:
        """Return dictionary representation of the model."""
        return self.build().dict(**kwargs)

    def json(self, **kwargs) -> str:
        """Return JSON representation of the model."""
        return self.build().json(**kwargs)

    @staticmethod
    def api_url() -> str:
        """Return the API URL for basic profile configuration."""
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/basic"

