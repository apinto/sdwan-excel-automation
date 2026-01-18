from .cgroup import ConfigGroupBuilder
import pandas as pd
import json
import logging
import ast
from typing import Dict, List, Optional

def parse_value(raw):
    """
    Custom parser for Excel cell values.
    - Handles None/NaN values.
    - Parses JSON/list-like strings (e.g., "[]" or "['item1', 'item2']")
    - Otherwise, returns the value as a string.
    """
    if pd.isna(raw):
        return None
    
    # Ensure we're working with a string representation
    val_str = str(raw).strip()
    
    # Handle empty values
    if not val_str:
        return None
  
    # Try to parse as JSON or Python literal if it looks like a list or dict
    if (val_str.startswith('[') and val_str.endswith(']')) or \
       (val_str.startswith('{') and val_str.endswith('}')):
        try:
            # Try JSON first
            return json.loads(val_str)
        except json.JSONDecodeError:
            try:
                # Try Python literal eval as fallback
                return ast.literal_eval(val_str)
            except (SyntaxError, ValueError):
                # If both fail, return as string
                return val_str
    
    # Handle numeric conversion
    if val_str.isdigit():
        return int(val_str)
    try:
        return float(val_str)
    except (ValueError, TypeError):
        # If all conversions fail, return the original string
        return val_str


def extract_field(row, field_name):
    """Extract a field from a row, handling NaN values"""
    if field_name not in row:
        return None
    
    value = row[field_name]
    # Handle different types of values
    if isinstance(value, list):
        # If it's already a list (e.g., of dicts for unsupportedFeatures), return as is
        return value
    elif pd.isna(value):
        return None
    
    return parse_value(value)


def parse_excel_to_config_group_builders(df, objects_df=None) -> List[ConfigGroupBuilder]:
    """
    Returns a list of ConfigGroupBuilder instances based on the DataFrame input
    
    Expected Excel format:
    - Name: Config group name
    - Description: Description text
    - solution: Solution type (sdwan)
    - site_devices: Number of site devices
    - deviceX.Tag: Tag for device X
    - deviceX.unsupportedFeatures: Can be in any of these formats:
        1. A list of feature IDs as strings
        2. A list of dictionaries with 'parcelType' and 'parcelId' keys
        3. A string in the format '["parcelType": "featureId", "parcelType": "featureId"]'
    - system, transport, policy, service, cli, uc, other: Profile IDs
    
    Args:
        df: DataFrame containing config group data
        objects_df: Optional DataFrame containing objects_created.xlsx data (not used directly in this function)
        
    Notes:
        - The function supports multiple formats for unsupportedFeatures to maintain backward compatibility
        - When using the custom string format with parcelType and parcelId, the function will parse it correctly
    """
    builders = []
    
    for _, row in df.iterrows():
        name = extract_field(row, 'Name')
        if not name:
            logging.warning("Skipping row with missing Name field")
            continue
        
        description = extract_field(row, 'Description') or f"Configuration Group for {name}"
        solution = extract_field(row, 'solution') or "sdwan"
        
        # Parse site_devices
        site_devices = 1
        if 'site_devices' in df.columns:
            site_value = extract_field(row, 'site_devices')
            if isinstance(site_value, (int, float)):
                site_devices = int(site_value)
        
        # Extract device information
        devices = []
        device_index = 1
        while f"device{device_index}.Tag" in df.columns:
            tag_field = f"device{device_index}.Tag"
            unsupported_field = f"device{device_index}.unsupportedFeatures"
            
            tag = extract_field(row, tag_field)
            if tag:
                device = {"tag": tag}
                
                # Extract unsupported features if present
                if unsupported_field in df.columns:
                    unsupported = extract_field(row, unsupported_field)
                    if unsupported is not None:
                        # Handle multiple formats of unsupported features
                        
                        # Format 1: Already a list of dictionaries with parcelType and parcelId
                        if (isinstance(unsupported, list) and 
                            len(unsupported) > 0 and 
                            isinstance(unsupported[0], dict) and 
                            "parcelType" in unsupported[0] and 
                            "parcelId" in unsupported[0]):
                            # It's already in the correct format
                            pass
                            
                        # Format 2: String that needs parsing
                        elif isinstance(unsupported, str):
                            try:
                                # Special handling for the format ["parcelType": "id", "parcelType": "id"]
                                if ':' in unsupported and '"' in unsupported:
                                    # This might be a custom format like:
                                    # '["wan/vpn/interface/ethernet": "Branch_WAN.vpn_0.interface_2", "wan/vpn/interface/ethernet": "Branch_WAN.vpn_0.interface_4"]'
                                    
                                    # Extract parcel types and IDs
                                    import re
                                    pattern = r'"([^"]+)":\s*"([^"]+)"'
                                    matches = re.findall(pattern, unsupported)
                                    
                                    if matches:
                                        # Convert to list of dictionaries
                                        unsupported = [{"parcelType": parcel_type, "parcelId": parcel_id} for parcel_type, parcel_id in matches]
                                    else:
                                        # If regex didn't work, try standard parsing
                                        if unsupported.startswith('[') and unsupported.endswith(']'):
                                            try:
                                                # Try to parse as JSON
                                                import json
                                                unsupported = json.loads(unsupported)
                                            except:
                                                try:
                                                    # Try to parse as Python literal
                                                    import ast
                                                    unsupported = ast.literal_eval(unsupported)
                                                except:
                                                    # Keep as a single item if all parsing fails
                                                    unsupported = [unsupported]
                                        else:
                                            # Single item, not a list
                                            unsupported = [unsupported]
                                else:
                                    # Standard JSON or Python list format
                                    if unsupported.startswith('[') and unsupported.endswith(']'):
                                        try:
                                            # Try to parse as JSON
                                            import json
                                            unsupported = json.loads(unsupported)
                                        except:
                                            try:
                                                # Try to parse as Python literal
                                                import ast
                                                unsupported = ast.literal_eval(unsupported)
                                            except:
                                                # Keep as a single item if all parsing fails
                                                unsupported = [unsupported]
                                    else:
                                        # Single item, not a list
                                        unsupported = [unsupported]
                            except Exception as e:
                                logging.warning(f"Error parsing unsupported features: {e}")
                                # Fall back to treating as a single item
                                unsupported = [unsupported]
                                
                        # Format 3: Any other value (ensure it's a list)
                        if not isinstance(unsupported, list):
                            unsupported = [unsupported]
                        
                        # Store in the device dict
                        device["unsupportedFeatures"] = unsupported
                
                devices.append(device)
            
            device_index += 1
        
        # Extract profiles - these are the references to other module profiles
        profiles = []
        profile_types = ['system', 'transport', 'policy', 'service', 'cli', 'uc', 'other']
        
        for profile_type in profile_types:
            if profile_type in df.columns:
                profile_id = extract_field(row, profile_type)
                if profile_id:
                    profiles.append(profile_id)
        
        # Create builder
        builder = ConfigGroupBuilder(
            name=name,
            description=description,
            solution=solution,
            devices=devices,
            site_devices=site_devices,
            profiles=profiles
        )
        
        builders.append(builder)
    
    return builders


'''
# Example usage
if __name__ == "__main__":
    import pandas as pd
    
    # Create a sample DataFrame simulating Excel data
    data = {
        "Name": ["CG-PEQM-ANEPC-112"],
        "Description": ["PEQM ANEPC 112 MS"],
        "solution": ["sdwan"],
        "site_devices": [2],
        "device1.Tag": ["EdgeDevice_01"],
        "device1.unsupportedFeatures": ["[]"],
        "device2.Tag": ["EdgeDevice_02"],
        "device2.unsupportedFeatures": ["[]"],
        "system": ["system-profile-rnsi"],
        "transport": ["transport-profile-rnsi"],
        "policy": [""],
        "service": ["SP-ANEPC-112-MS"],
        "cli": [""],
        "uc": [""],
        "other": [""]
    }
    
    df = pd.DataFrame(data)
    
    # Parse the DataFrame into builders
    builders = parse_excel_to_config_group_builders(df)
    
    # Print the resulting JSON for each builder
    for builder in builders:
        print(f"Config Group: {builder.name}")
        print(builder.json())
        print("=" * 50)
'''
