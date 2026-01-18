from pydantic import BaseModel, Field
from typing import List, Optional, Any


class UnsupportedFeature(BaseModel):
    parcelType: str
    parcelId: str


class Criteria(BaseModel):
    attribute: str
    value: str


class Device(BaseModel):
    criteria: Criteria
    unsupportedFeatures: Optional[List[UnsupportedFeature]] = None


class Topology(BaseModel):
    devices: List[Device]
    siteDevices: int



class Profile(BaseModel):
    id: str

class ConfigGroup(BaseModel):
    name: str
    description: str
    solution: str = Field(default="sdwan")
    topology: Optional[Topology] = None
    profiles: Optional[List[Profile]] = None


class ConfigGroupBuilder:
    def __init__(
        self,
        name: str,
        description: str,
        solution: str = "sdwan",
        devices: Optional[List[dict]] = None,
        site_devices: int = 1,
        profiles: Optional[List[str]] = None,
    ):
        """
        Initialize a ConfigGroupBuilder for creating configuration groups.
        
        Args:
            name: Name of the configuration group
            description: Description of the configuration group
            solution: Solution type (default: "sdwan")
            devices: List of device dictionaries with "tag" and optional "unsupportedFeatures" keys
            site_devices: Number of devices per site (default: 1)
            profiles: List of profile IDs to associate with this configuration group
        """
        self.name = name
        
        # Build topology model
        topology = None
        if devices:
            devices_models = []
            for device in devices:
                # Skip if tag is missing
                if "tag" not in device:
                    continue
                    
                # Process unsupported features
                unsupported_features = None
                if "unsupportedFeatures" in device and device["unsupportedFeatures"]:
                    # Handle empty list case
                    if isinstance(device["unsupportedFeatures"], list) and not device["unsupportedFeatures"]:
                        unsupported_features = None
                    else:
                        unsupported_list = device["unsupportedFeatures"]
                        
                        # Check if the items are already formatted as dictionaries with parcelType and parcelId
                        if isinstance(unsupported_list, list) and all(
                            isinstance(item, dict) and "parcelType" in item and "parcelId" in item
                            for item in unsupported_list
                        ):
                            unsupported_features = [
                                UnsupportedFeature(parcelType=item["parcelType"], parcelId=item["parcelId"])
                                for item in unsupported_list
                            ]
                        else:
                            # Legacy format: string IDs that need to be wrapped with default parcelType
                            unsupported_features = [
                                UnsupportedFeature(parcelType="wan/vpn/interface/ethernet", parcelId=parcel_id)
                                for parcel_id in unsupported_list
                            ]

                devices_models.append(
                    Device(
                        criteria=Criteria(attribute="tag", value=device["tag"]),
                        unsupportedFeatures=unsupported_features
                    )
                )

            if devices_models:
                topology = Topology(devices=devices_models, siteDevices=site_devices)

        # Build profiles as a list of Profile objects (with id field)
        profiles_models = None
        if profiles:
            valid_profiles = [p for p in profiles if p]
            if valid_profiles:
                profiles_models = [Profile(id=p_id) for p_id in valid_profiles]

        # Create the configuration group model
        self._model = ConfigGroup(
            name=name,
            description=description,
            solution=solution.lower(),  # Normalize solution name
            topology=topology,
            profiles=profiles_models,
        )

    def build(self) -> ConfigGroup:
        return self._model

    def dict(self) -> dict:
        return self._model.model_dump(exclude_none=True)

    def json(self) -> str:
        return self._model.model_dump_json(indent=2, exclude_none=True)
    
    @staticmethod
    def api_url() -> str:
        return "/dataservice/v1/config-group"


'''
# Example usage
builder = ConfigGroupBuilder(
    name="CG-PEQM-ANEPC-112",
    description="PEQM ANEPC 112 MS",
    solution="sdwan",
    devices=[
        {"tag": "EdgeDevice_01", "unsupportedFeatures": []},
        {"tag": "EdgeDevice_02", "unsupportedFeatures": []}
    ],
    site_devices=2,
    profiles=[
        "system-profile-rnsi",
        "transport-profile-rnsi",
        "SP-ANEPC-112-MS"
    ]
)

print(builder.json())
print(builder.api_url())
'''