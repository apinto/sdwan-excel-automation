from .profile import SysProfileBuilder
from .globall import GlobalBuilder
from .aaa import AaaBuilder  
from .bfd import BfdBuilder
from .omp import OmpBuilder
from .basic import BasicBuilder
from .banner import BannerBuilder
from .ntp import NtpBuilder
from .logg import LoggBuilder
from .snmp import SnmpBuilder
from .security import SecurityBuilder

import pandas as pd
import re
import logging
from typing import Any

def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def parse_value(raw):
    """Parse a value from Excel according to these rules:
    - None/NaN values become None
    - Numbers stay as numbers (1 stays as 1, not converted to True)
    - Strings with commas become lists
    - Only explicit 'true'/'false' become boolean
    - Everything else stays as is

    Note on Excel numeric values:
    When reading numeric values from Excel that should not be interpreted as booleans
    (like '1' that should stay as number 1, not become True), ensure the Excel cells
    are formatted as 'Text' or enter them with a leading quote ('1). Otherwise, Excel's
    numeric format might cause unintended boolean conversion during data loading.
    """
    if pd.isna(raw):
        return None
        
    # Handle numeric values first
    if isinstance(raw, (int, float)):
        return raw
        
    if isinstance(raw, str):
        stripped = raw.strip()
        
        # Handle comma-separated lists
        if "," in stripped:
            return [v.strip() for v in stripped.split(",")]
            
        # Handle boolean string values
        lowered = stripped.lower()
        if lowered in ["true", "false"]:
            return lowered == "true"
            
        # Handle numeric values - must be clean integers or floats
        try:
            # First check if it's a clean numeric string
            if stripped.startswith("-"):  # Handle negative numbers
                numeric_part = stripped[1:]
            else:
                numeric_part = stripped
                
            # For floats, allow only one decimal point
            if numeric_part.count(".") <= 1 and all(c.isdigit() or c == "." for c in numeric_part):
                if "." in stripped:
                    return float(stripped)
                else:
                    return int(stripped)
        except ValueError:
            pass
                
        # Not a special case, return as is
        return stripped
        
    # Not a string (already a number, bool, etc), return as is
    return raw

def extract_field(row, field_name):
    return str(row[field_name]).strip() if not pd.isna(row[field_name]) else None

def parse_excel_to_sys_profile_builder(df) -> SysProfileBuilder:
    """Parse Excel and return a SysProfileBuilder instance"""
    
    for _, row in df.iterrows():
        if row['ObjectName'] == 'System Profile' and row['Type'] == 'main':
            name = str(row['Name']).strip()
            description = str(row['Description']).strip()
            builder = SysProfileBuilder(name=name, description=description)

    logging.getLogger('json_payload').info(f"json payload: {builder.json()}")
    return builder

def parse_excel_to_global_builder(df) -> GlobalBuilder:
    """Parse Excel and return a GlobalBuilder instance"""
    
    # Filter for the main entry to get name and description
    main_entry = df[df['Type'] == 'global'].iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = GlobalBuilder(name=name, description=description)

    # Filter for rows that contain actual data to be parsed
    data_df = df[(df['Type'] == 'global') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        value = parse_value(row['value'])
        
        # All fields in the provided Excel seem to fall under this path
        path = "data.services_global.services_ip"
        
        builder.set_path_option(path, field, option_type, value)
    
    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

def parse_excel_to_aaa_builder(df) -> AaaBuilder:
    ''' returns a AaaBuilder instance based on the DataFrame input '''
    
    # Filter for the main entry to get name and description
    main_entry = df[df['Type'] == 'aaa'].iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = AaaBuilder(name=name, description=description)

    # Filter for rows that contain actual data to be parsed
    data_df = df[(df['Type'] == 'aaa') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        section = str(row['section']).strip()
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        value = parse_value(row['value'])
        
        # The section column now directly maps to our path
        path = section
        
        builder.set_path_option(path, field, option_type, value)
    
    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

def parse_excel_to_bfd_builder(df) -> BfdBuilder:
    ''' returns a BfdBuilder instance based on the DataFrame input '''
    
    main_entry = df[df['Type'] == 'bfd'].iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = BfdBuilder(name=name, description=description)

    data_df = df[(df['Type'] == 'bfd') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        section = str(row['section']).strip()
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        value = parse_value(row['value'])
        
        path = ""
        if section == 'bfd_root':
            path = 'data'
        elif section.startswith('color.'):
            path = 'data.colors.' + section.split('.')[1]
        
        if path:
            builder.set_path_option(path, camel_to_snake(field), option_type, value)
    
    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

def parse_excel_to_omp_builder(df: pd.DataFrame) -> OmpBuilder:
    '''Parse DataFrame and return a configured OmpBuilder'''
    # Filter for the main entry to get name and description
    main_entries = df[df['Type'] == 'omp']
    if main_entries.empty:
        raise ValueError("No OMP configuration found in DataFrame")
        
    main_entry = main_entries.iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = OmpBuilder(name=name, description=description)

    # Filter for rows that contain actual data to be parsed
    data_df = df[(df['Type'] == 'omp') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        section = str(row['section']).strip() if not pd.isna(row['section']) else ""
        field = extract_field(row, 'fieldName')
        if not field:  # Skip rows without field names
            continue
            
        option_type = extract_field(row, 'optionType') or "default"
        value = parse_value(row['value'])
        
        # Handle path based on section - similar to other parsers
        path = ""
        if section == "omp_root" or not section:
            path = ""  # Root level fields like other parsers
        elif section in ["advertiseIpv4", "advertiseIpv6"]:
            path = section  # Nested protocol fields
            
        try:
            builder.set_path_option(path, field, option_type, value)
        except KeyError as e:
            logging.warning(f"Skipping invalid field: {e}")
    
    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

def parse_excel_to_basic_builder(df) -> BasicBuilder:
    """Parse Excel and return a BasicBuilder instance."""
    # Get the main entry for name/description
    main_entries = df[df['Type'] == 'basic']
    if main_entries.empty:
        raise ValueError("No basic entries found in DataFrame")
        
    main_entry = main_entries.iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = BasicBuilder(name=name, description=description)
    
    # Filter for rows that contain actual data
    data_df = df[(df['Type'] == 'basic') & (df['fieldName'].notna())]

    # Track affinity per VRF entries for pairing
    affinity_pairs = []

    for _, row in data_df.iterrows():
        section = str(row['section']).strip() if not pd.isna(row['section']) else ""
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        value = parse_value(row['value'])

        if not field or not option_type:
            continue

        try:
            if section.startswith("affinityPerVrf"):
                # Collect affinity entries to be paired later
                affinity_pairs.append((field, option_type, value))
                if len(affinity_pairs) == 2:  # We have a complete pair
                    group_num = next((x for x in affinity_pairs if x[0] == "affinityGroupNumber"), None)
                    vrf_range = next((x for x in affinity_pairs if x[0] == "vrfRange"), None)
                    if group_num and vrf_range:
                        builder.add_affinity_per_vrf(
                            affinity_group_number=(group_num[1], group_num[2]),
                            vrf_range=(vrf_range[1], vrf_range[2])
                        )
                    affinity_pairs = []
            else:
                # Use the standardized path-based approach
                builder.set_path_option(section, field, option_type, value)

        except (KeyError, ValueError) as e:
            logging.warning(f"Skipping invalid field: {e}")

    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

def parse_excel_to_banner_builder(df) -> BannerBuilder:
    """Parse Excel and return a BannerBuilder instance"""
    # Get the main entry for name/description
    main_entries = df[df['Type'] == 'banner']
    if main_entries.empty:
        raise ValueError("No banner entries found in DataFrame")
        
    main_entry = main_entries.iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = BannerBuilder(name=name, description=description)

    # Filter for rows that contain actual data
    data_df = df[(df['Type'] == 'banner') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        value = parse_value(row['value'])
        
        # Convert None to empty string for default banner fields
        if value is None:
            value = ""
            
        if field and option_type:  # Only process if we have both field and option_type
            try:
                builder.set_path_option("", field, option_type, value)
            except KeyError as e:
                logging.warning(f"Skipping invalid field: {e}")

    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

def parse_excel_to_ntp_builder(df) -> NtpBuilder:
    """Parse Excel and return an NtpBuilder instance."""
    # Get the main entry for name/description
    main_entries = df[df['Type'] == 'ntp']
    if main_entries.empty:
        raise ValueError("No NTP entries found in DataFrame")
        
    main_entry = main_entries.iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = NtpBuilder(name=name, description=description)
    
    # Filter for rows that contain actual data
    data_df = df[(df['Type'] == 'ntp') & (df['fieldName'].notna())]
    
    # Track grouped entries
    servers = {}
    auth_keys = {}

    for _, row in data_df.iterrows():
        section = str(row['section']).strip() if not pd.isna(row['section']) else ""
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType') or "default"
        value = parse_value(row['value'])

        if not field:  # Skip rows without field names
            continue

        try:
            if section.startswith("ntp_server."):
                # Group server configurations
                server_id = section.split(".")[1]
                servers.setdefault(server_id, {})[field] = (option_type, value)
                
            elif section.startswith("authentication."):
                # Group authentication key configurations
                auth_id = section.split(".")[1]
                # Ensure keyId is always an integer
                if field == "keyId" and value is not None:
                    try:
                        value = int(value)
                    except Exception:
                        pass
                auth_keys.setdefault(auth_id, {})[field] = (option_type, value)
                
            elif section == "authentication" and field == "trustedKeys":
                # Handle trusted keys list
                if isinstance(value, list):
                    value = [int(v) for v in value]
                elif value is not None:
                    try:
                        value = [int(value)]
                    except Exception:
                        value = [value]
                else:
                    value = []
                builder.set_trusted_keys(option_type, value)
                
            elif section == "leader":
                # Handle leader configuration
                builder.set_path_option(section, field, option_type, value)
                
            else:
                # Handle root level fields
                builder.set_path_option(section, field, option_type, value)

        except (KeyError, ValueError) as e:
            logging.warning(f"Skipping invalid field: {e}")

    # Process grouped configurations
    for item in servers.values():
        try:
            builder.add_server(
                name=item.get('name', ("default", None)),
                key=item.get('key', ("default", None)),
                vpn=item.get('vpn', ("default", None)),
                version=item.get('version', ("default", None)),
                source_interface=item.get('sourceInterface', ("default", None)),
                prefer=item.get('prefer', ("default", None)),
            )
        except Exception as e:
            logging.warning(f"Failed to add server configuration: {e}")

    for item in auth_keys.values():
        try:
            builder.add_authentication_key(
                keyId=item.get('keyId', ("default", None)),
                md5Value=item.get('md5Value', ("default", None)),
            )
        except Exception as e:
            logging.warning(f"Failed to add authentication key: {e}")

    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

def parse_excel_to_logg_builder(df) -> LoggBuilder:
    """Parse Excel and return a LoggBuilder instance.
    
    Args:
        df: DataFrame containing logging configuration data
        
    Returns:
        LoggBuilder: Configured logging builder instance
        
    Raises:
        ValueError: If no logging entries found in DataFrame
    """
    # First check if we have any logging entries
    logg_entries = df[df['Type'] == 'logg']
    if logg_entries.empty:
        raise ValueError("No logging entries found in DataFrame")
        
    # Get the main entry for name/description
    main_entry = logg_entries.iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = LoggBuilder(name=name, description=description)
    
    # Track grouped entries
    disk_file_entries = {}
    tls_profiles = {}
    servers = {}

    # Filter for rows that contain actual data
    data_df = df[(df['Type'] == 'logg') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        section = str(row['section']).strip() if not pd.isna(row['section']) else ""
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType') or "default"
        value = parse_value(row['value'])

        if not field:  # Skip rows without field names
            continue

        try:
            if section == "disk.file":
                # Group disk file settings
                disk_file_entries[field] = (option_type, value)
                
            elif section.startswith("tlsProfile."):
                # Group TLS profile settings
                tls_id = section.split(".")[1]
                tls_profiles.setdefault(tls_id, {})[field] = (option_type, value)
                
            elif section.startswith("logg_server."):
                # Group server settings
                server_id = section.split(".")[1]
                servers.setdefault(server_id, {})[field] = (option_type, value)
                
            else:
                # Handle any direct path settings
                path = ""
                if section and section != "logg_root":
                    path = section
                builder.set_path_option(path, field, option_type, value)

        except (KeyError, ValueError) as e:
            logging.warning(f"Skipping invalid field: {e}. Row: {row.to_dict()}")

    # Process disk file settings
    if disk_file_entries:
        try:
            builder.set_disk_file_options(
                disk_file_size=disk_file_entries.get("diskFileSize", ("default", 10)),
                disk_file_rotate=disk_file_entries.get("diskFileRotate", ("default", 10))
            )
        except Exception as e:
            logging.warning(f"Failed to set disk file options: {e}")

    # Process TLS profiles
    for item in tls_profiles.values():
        try:
            cipher_suite = item.get("cipherSuiteList", ("global", []))[1]
            # Handle comma-separated string to list conversion
            if isinstance(cipher_suite, str):
                cipher_suite = [v.strip() for v in cipher_suite.split(",")]
            builder.add_tls_profile(
                profile=item.get("profile", ("global", None)),
                tls_version=item.get("tlsVersion", ("default", None)),
                auth_type=item.get("authType", ("default", None)),
                cipher_suite_list=("global", cipher_suite)
            )
        except Exception as e:
            logging.warning(f"Failed to add TLS profile: {e}")

    # Process servers
    for item in servers.values():
        try:
            builder.add_server(
                name=item.get("name", ("global", None)),
                vpn=item.get("vpn", ("global", None)),
                source_interface=item.get("sourceInterface", ("default", None)),
                priority=item.get("priority", ("default", "informational")),
                tls_enable=item.get("tlsEnable", ("default", False))
            )
        except Exception as e:
            logging.warning(f"Failed to add server: {e}")

    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder


def parse_excel_to_security_builder(df) -> SecurityBuilder:
    ''' returns a SecurityBuilder instance based on the DataFrame input '''
    
    # Find security entry in the DataFrame - case insensitive matching for 'security' type
    security_entries = df[df['Type'].str.lower() == 'security']
    if security_entries.empty:
        logging.warning("No security entries found in Excel data.")
        # Return a default security builder with empty values
        return SecurityBuilder(name="Default-Security", description="Default Security Configuration")
    
    # Get the first row for name and description
    main_entry = security_entries.iloc[0]
    name = str(main_entry['Name']).strip() if not pd.isna(main_entry['Name']) else "Default-Security"
    description = str(main_entry['Description']).strip() if not pd.isna(main_entry['Description']) else ""
    
    builder = SecurityBuilder(name=name, description=description)

    # Filter for rows with security data - case insensitive matching
    data_df = df[(df['Type'].str.lower() == 'security') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        section = str(row['section']).strip() if not pd.isna(row['section']) else 'security_root'
        field_name = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType') or 'default'
        value = parse_value(row['value'])
        
        # Special handling for replayWindow - ensure it's a string
        if field_name == 'replayWindow' and not isinstance(value, str) and value is not None:
            value = str(value)
        
        # Handle array items like keychain.0 or key.0
        if '.' in field_name:
            base_field, rest = field_name.split('.', 1)
            if base_field in ['keychain', 'key']:
                # Check if this is a direct array index (like key.0)
                if rest.isdigit():
                    # Skip creating empty entries in arrays - let them remain as empty lists
                    # Only add actual items when we have specific fields to set
                    continue
                # Handle more complex cases like key.0.name
                elif '.' in rest:
                    idx_str, field = rest.split('.', 1)
                    if idx_str.isdigit():
                        idx = int(idx_str)
                        if base_field == 'keychain':
                            builder.set_keychain_field(idx, field, option_type, value)
                        elif base_field == 'key':
                            builder.set_key_field(idx, field, option_type, value)
                        continue
        
        if section == 'security_root':
            # Set top-level option (standard fields)
            builder.set_option(field_name, option_type, value)
        else:
            # Set nested option
            builder.set_nested_option(section, field_name, option_type, value)
    
    # Log the JSON payload
    json_payload = builder.json(indent=2)
    json_logger = logging.getLogger('json_payload')
    json_logger.info(f"Security json payload: {json_payload}")
    
    return builder

def parse_excel_to_snmp_builder(df) -> SnmpBuilder:
    """Parse Excel and return a SnmpBuilder instance.
    
    Args:
        df: DataFrame containing SNMP configuration data
        
    Returns:
        SnmpBuilder: Configured SNMP builder instance
        
    Raises:
        ValueError: If no SNMP entries found in DataFrame
    """
    # First check if we have any SNMP entries
    snmp_entries = df[df['Type'] == 'snmp']
    if snmp_entries.empty:
        raise ValueError("No SNMP entries found in DataFrame")
        
    # Get the main entry for name/description
    main_entry = snmp_entries.iloc[0]
    name = str(main_entry['Name']).strip()
    description = str(main_entry['Description']).strip()
    
    builder = SnmpBuilder(name=name, description=description)
    
    # Track grouped entries
    views = {}
    view_oids = {}
    communities = {}
    groups = {}
    users = {}
    targets = {}

    # Filter for rows that contain actual data
    data_df = df[(df['Type'] == 'snmp') & (df['fieldName'].notna())]

    for _, row in data_df.iterrows():
        section = str(row['section']).strip() if not pd.isna(row['section']) else ""
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType') or "default"
        value = parse_value(row['value'])

        try:
            if section == "snmp_root":
                # Handle root level fields
                if field and option_type:
                    # Use set_path_option with empty path for root level fields
                    builder.set_path_option("", field, option_type, value)
                    
            elif section.startswith("snmp_view."):
                # Handle view and view OID entries
                parts = section.split(".")
                view_id = parts[1]
                if len(parts) == 2:  # View name entry
                    views.setdefault(view_id, {})[field] = (option_type, value)
                elif len(parts) == 4 and parts[2] == "oid":  # View OID entry
                    oid_id = parts[3]
                    view_oids.setdefault(view_id, {}).setdefault(oid_id, {})[field] = (option_type, value)
                    
            elif section.startswith("snmp_community."):
                # Handle community entries
                community_id = section.split(".")[1]
                communities.setdefault(community_id, {})[field] = (option_type, value)
                
            elif section.startswith("snmp_group."):
                # Handle group entries
                group_id = section.split(".")[1]
                groups.setdefault(group_id, {})[field] = (option_type, value)
                
            elif section.startswith("snmp_user."):
                # Handle user entries
                user_id = section.split(".")[1]
                users.setdefault(user_id, {})[field] = (option_type, value)
                
            elif section.startswith("snmp_target."):
                # Handle target entries
                target_id = section.split(".")[1]
                targets.setdefault(target_id, {})[field] = (option_type, value)
                
        except (KeyError, ValueError) as e:
            logging.warning(f"Skipping invalid field: {e}. Row: {row.to_dict()}")

    # Process views and their OIDs
    try:
        for view_id, view_fields in views.items():
            view_name = view_fields.get("name", ("global", None))
            oid_list = []
            for oid_fields in view_oids.get(view_id, {}).values():
                oid_id = oid_fields.get("id", ("global", None))
                exclude = oid_fields.get("exclude", ("default", False))
                oid_list.append({"id": oid_id, "exclude": exclude})
            builder.add_view(view_name, oid_list)
    except Exception as e:
        logging.warning(f"Failed to process views: {e}")

    # Process communities or groups/users based on configuration
    try:
        if communities:
            # Process communities if any exist
            for community_fields in communities.values():
                builder.add_community(
                    name=community_fields.get("name", ("global", None)),
                    userLabel=community_fields.get("userLabel", ("global", None)),
                    view=community_fields.get("view", ("global", None)),
                    authorization=community_fields.get("authorization", ("global", None))
                )
        else:
            # Process groups and users if no communities
            for group_fields in groups.values():
                builder.add_group(
                    name=group_fields.get("name", ("global", None)),
                    securityLevel=group_fields.get("securityLevel", ("global", None)),
                    view=group_fields.get("view", ("global", None))
                )
            for user_fields in users.values():
                builder.add_user(
                    name=user_fields.get("name", ("global", None)),
                    auth=user_fields.get("auth", ("global", None)),
                    authPassword=user_fields.get("authPassword", ("global", None)),
                    priv=user_fields.get("priv", ("global", None)),
                    privPassword=user_fields.get("privPassword", ("global", None)),
                    group=user_fields.get("group", ("global", None))
                )
    except Exception as e:
        logging.warning(f"Failed to process communities/groups/users: {e}")

    # Process targets
    try:
        for target_fields in targets.values():
            builder.add_target(
                vpnId=target_fields.get("vpnId", ("global", None)),
                ip=target_fields.get("ip", ("global", None)),
                port=target_fields.get("port", ("global", None)),
                user=target_fields.get("user", ("global", None)),
                sourceInterface=target_fields.get("sourceInterface", ("variable", None))
            )
    except Exception as e:
        logging.warning(f"Failed to process targets: {e}")

    logging.getLogger('json_payload').info(f"json payload: {builder.json(indent=2)}")
    return builder

