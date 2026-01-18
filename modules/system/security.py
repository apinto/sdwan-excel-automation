from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_serializer, ConfigDict, model_validator

class OptionValue(BaseModel):
    """Model for option-value pairs with optionType handling."""
    optionType: str
    value: Optional[Any] = None
    model_config = ConfigDict(extra="forbid")
    
    @field_serializer("value")
    def serialize_value(self, v):
        # Handle variable type
        if self.optionType == "variable" and isinstance(v, str):
            if not v.startswith("{{") and not v.endswith("}}"):
                return f"{{{{{v}}}}}"
        
        # Special case for replayWindow - always convert to string
        # Access the parent model to check if this field is replayWindow
        field_name = getattr(self, '_parent_field_name', None)
        if field_name == 'replayWindow' and not isinstance(v, str):
            return str(v)
        
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

class Key(BaseModel):
    """Model for security key."""
    # Common fields for key entries
    id: Optional[OptionValue] = None
    type: Optional[OptionValue] = None
    name: Optional[OptionValue] = None
    value: Optional[OptionValue] = None
    model_config = ConfigDict(extra="forbid")

class Keychain(BaseModel):
    """Model for security keychain."""
    # Common fields for keychain entries
    id: Optional[OptionValue] = None
    name: Optional[OptionValue] = None
    key_string: Optional[OptionValue] = Field(None, alias="keyString")
    send_id: Optional[OptionValue] = Field(None, alias="sendId")
    send_lifetime: Optional[OptionValue] = Field(None, alias="sendLifetime")
    model_config = ConfigDict(extra="forbid")

class SecurityData(BaseModel):
    """Model for security configuration data."""
    rekey: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=86400))
    replayWindow: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value="512"))  # Keep as string
    integrityType: OptionValue = Field(default_factory=lambda: OptionValue(optionType="global", value=["ip-udp-esp", "esp"]))
    pairwiseKeying: OptionValue = Field(default_factory=lambda: OptionValue(optionType="default", value=False))
    keychain: List[Keychain] = Field(default_factory=list)
    key: List[Key] = Field(default_factory=list)
    
    @model_validator(mode="after")
    def track_field_names(self):
        """Add parent field name to each OptionValue for better serialization control."""
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, OptionValue):
                setattr(field_value, '_parent_field_name', field_name)
        return self
    model_config = ConfigDict(extra="forbid")

class SecurityModel(BaseModel):
    """Model for security configuration."""
    name: str
    description: str
    data: SecurityData = Field(default_factory=SecurityData)
    model_config = ConfigDict(extra="forbid")

class SecurityBuilder:
    """Builder for security configuration."""
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize the SecurityBuilder.
        
        Args:
            name: Name of the security configuration
            description: Description for the security configuration
        """
        self.name = name
        self.description = description
        self.data = SecurityData()
    
    def set_option(self, field: str, option_type: str, value: Any) -> "SecurityBuilder":
        """
        Set an option in the root level of security configuration.
        
        Args:
            field: Field to set
            option_type: Option type (default, global, variable)
            value: Value to set
            
        Returns:
            Self for chaining
        """
        if hasattr(self.data, field):
            setattr(self.data, field, OptionValue(optionType=option_type, value=value))
        else:
            raise KeyError(f"Invalid field: {field}")
        return self
        
    def set_nested_option(self, path: str, field: str, option_type: str, value: Any) -> "SecurityBuilder":
        """
        Set an option in a nested attribute.
        
        Args:
            path: Dot-separated path to the nested attribute
            field: Field to set in the target
            option_type: Option type (default, global, variable)
            value: Value to set
            
        Returns:
            Self for chaining
        """
        current = self.data
        
        if not path:
            return self.set_option(field, option_type, value)
            
        parts = path.split('.')
        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Invalid path: {path}, {part} not found")
                
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
        return self
            
    def add_key(self, key_config: dict = None) -> int:
        """
        Add a key entry and return its index.
        
        Args:
            key_config: Dictionary with key configuration (optional)
        
        Returns:
            The index of the newly added key
        """
        key_config = key_config or {}
        key = Key(**key_config)
        self.data.key.append(key)
        return len(self.data.key) - 1
        
    def add_keychain(self, keychain_config: dict = None) -> int:
        """
        Add a keychain entry and return its index.
        
        Args:
            keychain_config: Dictionary with keychain configuration (optional)
            
        Returns:
            The index of the newly added keychain
        """
        keychain_config = keychain_config or {}
        keychain = Keychain(**keychain_config)
        self.data.keychain.append(keychain)
        return len(self.data.keychain) - 1
        
    def set_key_field(self, index: int, field: str, option_type: str, value: Any) -> "SecurityBuilder":
        """
        Set a field in a specific key entry.
        
        Args:
            index: The index of the key to modify
            field: Field to set
            option_type: Option type (default, global, variable)
            value: Value to set
            
        Returns:
            Self for chaining
        """
        # Make sure the key exists
        while len(self.data.key) <= index:
            self.add_key()
            
        key = self.data.key[index]
        if hasattr(key, field):
            setattr(key, field, OptionValue(optionType=option_type, value=value))
        return self
        
    def set_keychain_field(self, index: int, field: str, option_type: str, value: Any) -> "SecurityBuilder":
        """
        Set a field in a specific keychain entry.
        
        Args:
            index: The index of the keychain to modify
            field: Field to set
            option_type: Option type (default, global, variable)
            value: Value to set
            
        Returns:
            Self for chaining
        """
        # Make sure the keychain exists
        while len(self.data.keychain) <= index:
            self.add_keychain()
            
        keychain = self.data.keychain[index]
        if hasattr(keychain, field):
            setattr(keychain, field, OptionValue(optionType=option_type, value=value))
        return self
        
    def build(self) -> SecurityModel:
        """Build and return the SecurityModel instance."""
        # Remove empty objects from lists to ensure they appear as [] not [{}]
        if not any(self.data.keychain):
            self.data.keychain = []
        if not any(self.data.key):
            self.data.key = []
            
        return SecurityModel(
            name=self.name,
            description=self.description,
            data=self.data
        )

    def dict(self, **kwargs) -> dict:
        """Return dictionary representation of the model."""
        model = self.build()
        return model.model_dump(exclude_none=True, **kwargs)

    def json(self, **kwargs) -> str:
        """Return JSON representation of the model."""
        model = self.build()
        return model.model_dump_json(exclude_none=True, **kwargs)

    @staticmethod
    def api_url() -> str:
        """Return the API URL for security configuration."""
        return "/dataservice/v1/feature-profile/sdwan/system/{systemId}/security"
