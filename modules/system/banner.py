from typing import Any, Optional
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

class BannerDataModel(BaseModel):
    """Model for banner data settings."""
    login: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=""))
    motd: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=""))
    model_config = ConfigDict(extra="forbid")

class BannerModel(BaseModel):
    """Root model for banner configuration."""
    name: str
    description: str
    data: BannerDataModel = Field(default_factory=BannerDataModel)
    model_config = ConfigDict(extra="forbid")

class BannerBuilder:
    def __init__(self, name: str, description: str):
        """Initialize the builder with name and description."""
        self.name = name
        self.description = description
        self.data = BannerDataModel()  # Uses default values from model

    def set_path_option(self, path: str, field: str, option_type: str, value: Any) -> None:
        """
        Set an option at a given path with proper optionType handling.
        
        Args:
            path: Not used in banner as there's no nesting
            field: Field name to set (login or motd)
            option_type: Type of option ("default", "global", "variable")
            value: Value to set
        """
        if option_type == "default":
            value = ""  # Always set default to empty string for banner
            
        if hasattr(self.data, field):
            setattr(self.data, field, OptionValue(optionType=option_type, value=value))
        else:
            raise KeyError(f"Invalid field: {field}")

    def build(self) -> BannerModel:
        """Build and return the BannerModel instance."""
        return BannerModel(
            name=self.name,
            description=self.description,
            data=self.data
        )

    def dict(self, **kwargs) -> dict:
        return self.build().model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        return self.build().model_dump_json(exclude_none=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/banner"

