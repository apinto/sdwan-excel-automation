#!/usr/bin/env python

# Author: Artur Pinto (arturj.pinto@gmail.com)

import warnings
warnings.filterwarnings('ignore', message='.*Signature.*for.*longdouble.*')

import logging
import sys

# Configure logging system
# Set up a consistent formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Configure the root logger for general messages
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Remove any existing handlers to avoid duplicates
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
    
# Add console handler for user output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

# Add file handler for all logs
file_handler = logging.FileHandler("vmanager_conf.log", mode='a')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)  # Capture more detailed logs in file
root_logger.addHandler(file_handler)

# Create a separate logger for detailed JSON payloads
json_logger = logging.getLogger('json_payload')
json_logger.setLevel(logging.DEBUG)
json_logger.propagate = False  # Don't send to root logger
# Remove any existing handlers to avoid duplicates
for handler in json_logger.handlers[:]:
    json_logger.removeHandler(handler)
# Only log JSON details to file
json_file_handler = logging.FileHandler("vmanager_conf.log", mode='a')
json_file_handler.setFormatter(formatter)
json_logger.addHandler(json_file_handler)


from modules.system.parsers import (
    parse_excel_to_sys_profile_builder,
    parse_excel_to_global_builder,
    parse_excel_to_aaa_builder,
    parse_excel_to_bfd_builder,
    parse_excel_to_omp_builder,
    parse_excel_to_basic_builder,
    parse_excel_to_banner_builder,
    parse_excel_to_ntp_builder,
    parse_excel_to_logg_builder,
    parse_excel_to_snmp_builder,
    parse_excel_to_security_builder,
)

from modules.transport.parsers import (
    parse_excel_to_transport_profile_builder,
    parse_excel_to_vpn_builder,
    parse_excel_to_interface_builders, 
    parse_excel_to_bgp_builder,
)

from modules.service.parsers import (
    parse_excel_to_service_profile_builders,
    parse_excel_to_service_vpn_builders,
    parse_excel_to_service_interface_builders,
)

from modules.cli.parsers import (
    parse_excel_to_cli_profiles_builder,
    parse_excel_to_cli_builder,
)


from modules.conf_groups.parsers import (
    parse_excel_to_config_group_builders,
)

from catalystwan.session import create_manager_session
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import pandas as pd
import argparse
from pathlib import Path
import time
import datetime

url      = "https://your-vmanager-ip"
username = "your-username"
password = "your-password"

# Create a global list to track created objects
created_objects = []

# Create a global dictionary to track objects by type for current execution summary
current_run_summary = {}

# Generate a unique run ID based on the current epoch time
run_id = int(time.time())
# Create a user-friendly timestamp
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def post_vmanager(prf_type, url, username, password, main_builder, parcel_builders, subparcel_builders=None):

    def _log_and_post(session, action, object_name, api_url, payload, parent_profile=None):
        """Helper function to post data and log the action, respecting log separation."""
        try:
            # Log request details to debug file only
            json_logger.debug(f"REQUEST: {action} {object_name} | URL: {api_url}")
            json_logger.debug(f"REQUEST PAYLOAD: {payload}")
            
            # Make the API call
            resp = session.post(api_url, json=payload)
            resp.raise_for_status()
            
            # Handle different response types
            resp_text = resp.text if hasattr(resp, "text") else "No text body"
            json_logger.debug(f"RESPONSE TEXT: {resp_text}")
            
            try:
                resp_json = resp.json()
            except Exception as e:
                # For non-JSON responses, create an empty dict
                json_logger.debug(f"Response is not JSON: {e}")
                resp_json = {}
            
            # Extract object ID from response
            object_id = resp_json.get('id') or resp_json.get('profileId') or resp_json.get('parcelId')
            
            # Log concise success message to console 
            logging.info(f"SUCCESS: {action} {object_name} | STATUS: {resp.status_code}")
            # Log detailed success with response to file only
            json_logger.debug(f"RESPONSE: {action} {object_name} | URL: {api_url} | STATUS: {resp.status_code} | BODY: {resp_json}")
            
            # Format the full object name for tracking, including parent profile context
            # Debug the raw response body
            json_logger.debug(f"DEBUG RAW RESPONSE BODY: {resp.text if hasattr(resp, "text") else "No text body"}")
            full_object_name = object_name
            if " in " in object_name:
                # For cases like "Create Interface Parcel 'X' in VPN 'Y' of Profile 'Z'"
                full_object_name = f"{action} {object_name}"
            elif parent_profile and action.startswith("Create") and "Parcel" in action:
                # For parcel cases with a parent profile, like "Create System Parcel for global"
                # We'll format it to show the relationship
                full_object_name = f"{action} for {object_name} in {parent_profile}"
            else:
                # For simpler cases like "Create Service Profile X"
                full_object_name = f"{action} for {object_name}"
            
            # For BGP associations, use the parcelId from the payload
            if action == "Associate BGP Parcel":
                json_logger.debug(f"BGP ASSOCIATION: object_id={object_id}, payload={payload}")
                if payload.get('parcelId'):
                    # This is the special case for BGP associations
                    # Add a suffix to the ID to make it unique from the BGP Parcel create operation
                    object_id = payload.get('parcelId') + "-assoc"
                    json_logger.debug(f"Using modified parcelId for BGP association: {object_id}")
                    
                # Force log regardless of whether we found an ID
                logging.info(f"BGP Association tracking: object_id={object_id}, action={action}, name={full_object_name}")
                
            # Add to our tracking list if we have an ID
            if object_id:
                created_objects.append({
                    'Object Name': full_object_name,
                    'URL': api_url,
                    'ID': object_id,
                    'Run ID': run_id,
                    'Timestamp': timestamp
                })
                
                # Track for current run summary - extract object type and parcel type
                object_type = "Unknown"
                parcel_type = "Unknown"
                
                # Special handling for BGP associations first
                if action == "Associate BGP Parcel":
                    object_type = 'Transport'
                    parcel_type = 'BGP-Association'
                else:
                    # Extract Object Type based on URL path components
                    if '/system/' in api_url:
                        object_type = 'System'
                    elif '/transport/' in api_url:
                        object_type = 'Transport'
                    elif '/service/' in api_url:
                        object_type = 'Service'
                    elif '/cli/' in api_url:
                        object_type = 'CLI'
                    elif '/config-group' in api_url:
                        object_type = 'ConfigGroup'
                    
                    # Extract Parcel Type based on URL pattern and action
                    # More specific checks first, then fallbacks
                    if '/transport/' in api_url:
                        if '/routing/bgp' in api_url:
                            parcel_type = 'BGP'
                        elif '/routing/' in api_url:
                            parcel_type = api_url.split('/')[-1]
                        elif '/interface/' in api_url:
                            parcel_type = 'Interface'
                        elif api_url.endswith('/vpn') or '/vpn/' in api_url:
                            parcel_type = 'VPN'
                        elif api_url.endswith('/') and 'feature-profile/sdwan/transport/' in api_url and api_url.count('/') <= 6:
                            parcel_type = 'Profile'
                        else:
                            parcel_type = 'Unknown'
                    elif '/system/' in api_url:
                        if api_url.endswith('/') and 'feature-profile/sdwan/system/' in api_url and api_url.count('/') <= 6:
                            parcel_type = 'Profile'
                        elif len(api_url.split('/')) >= 7:
                            parcel_type = api_url.split('/')[-1]
                    elif '/service/' in api_url:
                        if api_url.endswith('/') and 'feature-profile/sdwan/service/' in api_url and api_url.count('/') <= 6:
                            parcel_type = 'Profile'
                        elif '/lan/vpn' in api_url and api_url.endswith('/vpn'):
                            parcel_type = 'VPN'
                        elif '/interface/' in api_url:
                            parcel_type = 'Interface'
                    elif '/cli/' in api_url:
                        if api_url.endswith('/') and 'cli' in api_url:
                            parcel_type = 'Profile'
                        elif '/config' in api_url:
                            parcel_type = 'Config'
                    elif '/config-group' in api_url:
                        parcel_type = 'Profile'
                    elif api_url.endswith('/'):
                        parcel_type = 'Profile'
                
                # Debug logging for classification issues
                json_logger.debug(f"CLASSIFICATION: action='{action}' | url='{api_url}' | object_type='{object_type}' | parcel_type='{parcel_type}'")
                if parcel_type == 'Unknown':
                    json_logger.warning(f"UNKNOWN PARCEL TYPE: action='{action}' | url='{api_url}' | object_name='{object_name}'")
                if object_type == 'Transport' and parcel_type == 'Profile' and not ('feature-profile/transport' in api_url and api_url.endswith('/')):
                    json_logger.warning(f"POTENTIAL MISCLASSIFICATION: action='{action}' | url='{api_url}' | classified_as='Transport Profile' but URL pattern unexpected")
                
                # Track the object creation
                track_created_object(object_type, parcel_type, action, object_name)
                
            return resp_json, resp.status_code
        except Exception as e:
            # Log error summary to console
            logging.error(f"FAILED: {action} {object_name} | ERROR: {e}")
            # Log detailed error info to file
            json_logger.error(f"FAILED: {action} {object_name} | URL: {api_url} | ERROR: {e}")
            
            # Attempt to get more detailed error from response if available
            try:
                if hasattr(resp, 'text'):
                    error_details = resp.text
                    json_logger.error(f"FAILED RESPONSE BODY: {error_details}")
            except Exception:
                pass
                
            # Save all objects created so far before exiting
            try:
                logging.warning("Saving created objects before exiting due to error...")
                save_created_objects_to_excel()
                logging.warning("Created objects saved successfully.")
            except Exception as save_error:
                logging.error(f"Failed to save created objects: {save_error}")
                
            sys.exit(e)

    # Always treat main_builder as a list for all types
    if not isinstance(main_builder, list):
        builders = [main_builder]
    else:
        builders = main_builder

    logging.info(f'################# Post {prf_type} Profile and parcels to vManager #################')
    try:
        with create_manager_session(url=url, username=username, password=password) as session:
            # ConfigGroup: handle configuration groups which reference other profiles by ID
            if prf_type.lower() in ["config-group"]:
                json_logger.debug(f"Processing {len(builders)} configuration group(s)")                
                for builder in builders:
                    group_name = builder.name
                    payload = builder.dict()
                    api_url = builder.api_url()
                    action = "Create Configuration Group"
                    
                    # Log the references to help with troubleshooting (only in debug file)
                    profiles = builder._model.profiles or []
                    for prof in profiles:
                        prof_id = getattr(prof, 'id', None)
                        prof_type = getattr(prof, 'type', None)
                        if prof_id and prof_type:
                            json_logger.debug(f"Configuration Group '{group_name}' references {prof_type} profile with ID: {prof_id}")
                    
                    _log_and_post(session, action, group_name, api_url, payload)
                return
            # CLI: handle profile and config
            if prf_type == "CLI":
                for builder in builders:
                    profile_name = builder.name
                    payload = builder.dict()
                    api_url = builder.api_url()
                    resp_json, _ = _log_and_post(session, "Create CLI Profile", profile_name, api_url, payload)
                    if 'profileId' in resp_json:
                        profile_id = resp_json['profileId']
                    elif 'id' in resp_json:
                        profile_id = resp_json['id']
                    else:
                        logging.error(f"Could not find profile ID in response for {profile_name}: {resp_json}")
                        raise KeyError("Could not find 'profileId' or 'id' in response")
                    
                    # Process CLI config builders if available
                    for cli_builder in parcel_builders:
                        # Access name from the model instead of directly
                        cli_name = cli_builder.model.name
                        if cli_name == profile_name:  # Match by name
                            cli_payload = cli_builder.dict()
                            cli_api_url = cli_builder.api_url().format(cliId=profile_id)
                            _log_and_post(session, "Create CLI Config", f"for profile {profile_name}", cli_api_url, cli_payload, parent_profile=profile_name)
                return
                
            # Service: handle profile and parcels
            if prf_type == "Service":
                for builder in builders:
                    profile_name = builder.name
                    payload = builder.dict()
                    api_url = builder.api_url()
                    resp_json, _ = _log_and_post(session, "Create Service Profile", profile_name, api_url, payload)
                    if 'profileId' in resp_json:
                        profile_id = resp_json['profileId']
                    elif 'id' in resp_json:
                        profile_id = resp_json['id']
                    else:
                        logging.error(f"Could not find profile ID in response for {profile_name}: {resp_json}")
                        raise KeyError("Could not find 'profileId' or 'id' in response")
                    
                    # Save objects immediately after creating the service profile
                    save_created_objects_to_excel()
                    
                    if parcel_builders and profile_name in parcel_builders:
                        for vpn_parcel_builder in parcel_builders[profile_name]:
                            vpn_payload = vpn_parcel_builder.dict()
                            vpn_api_url = vpn_parcel_builder.api_url().format(serviceId=profile_id)
                            vpn_name = vpn_parcel_builder._model.name
                            resp_vpn_json, _ = _log_and_post(session, f"Create VPN Parcel '{vpn_name}'", f"in {profile_name}", vpn_api_url, vpn_payload)
                            vpn_id = resp_vpn_json.get('parcelId')
                            if not vpn_id:
                                logging.warning(f"Could not create VPN parcel '{vpn_name}' or find its ID. Skipping dependent interface parcels.")
                                continue
                            
                            # Save objects immediately after creating each VPN
                            save_created_objects_to_excel()
                            
                            interface_key = (profile_name, vpn_name)
                            if subparcel_builders and interface_key in subparcel_builders:
                                for interface_builder in subparcel_builders[interface_key]:
                                    interface_payload = interface_builder.dict()
                                    interface_api_url = interface_builder.api_url(serviceId=profile_id, vpnId=vpn_id)
                                    interface_name = interface_builder.name
                                    _log_and_post(
                                        session, 
                                        f"Create Interface Parcel '{interface_name}'", 
                                        f"in VPN '{vpn_name}' of Profile '{profile_name}'", 
                                        interface_api_url, 
                                        interface_payload
                                    )
                                    
                                    # Save objects immediately after creating each interface
                                    save_created_objects_to_excel()
                                    
                return
            # All other types: single builder, handle parcels
            builder = builders[0]
            profile_name = builder.name
            payload = builder.dict()
            api_url = builder.api_url()
            resp_json, _ = _log_and_post(session, f"Create {prf_type} Profile", profile_name, api_url, payload)
            if 'profileId' in resp_json:
                profile_id = resp_json['profileId']
            elif 'id' in resp_json:
                profile_id = resp_json['id']
            else:
                logging.error(f"Could not find profile ID in response for {profile_name}: {resp_json}")
                raise KeyError("Could not find 'profileId' or 'id' in response")
            # --- Special handling for Transport profile dependencies ---
            if prf_type == "Transport":
                vpn_id = None
                actual_vpn_name = None  # Store the actual VPN name for later use
                for key, parcel_builder in parcel_builders.items():
                    if key.startswith("vpn") and parcel_builder:
                        parcel_payload = parcel_builder.dict()
                        parcel_api_url = parcel_builder.api_url().format(transportId=profile_id)
                        # Get the VPN name for better logging and tracking
                        actual_vpn_name = parcel_builder.name if hasattr(parcel_builder, 'name') else key
                        resp_parcel_json, _ = _log_and_post(session, "Create Transport VPN Parcel", actual_vpn_name, parcel_api_url, parcel_payload, parent_profile=profile_name)
                        vpn_id = resp_parcel_json.get('parcelId')
                        break 
                if not vpn_id:
                    logging.warning("Could not create VPN parcel or find its ID. Skipping dependent parcels.")
                    return
                for key, parcel_builder in parcel_builders.items():
                    if key.startswith("vpn"): # Already created
                        continue
                    if parcel_builder:
                        if key.startswith("interface"):
                            parcel_payload = parcel_builder.dict()
                            parcel_api_url = parcel_builder.api_url().format(transportId=profile_id, vpnId=vpn_id)
                            # Get the interface name for better logging and tracking
                            interface_name = parcel_builder.name if hasattr(parcel_builder, 'name') else key
                            # Use the actual VPN name saved earlier
                            # Format as Transport Profile > VPN > Interface
                            _log_and_post(session, "Create Interface Parcel", interface_name, parcel_api_url, parcel_payload, parent_profile=f"{profile_name}.{actual_vpn_name}")
                        elif key.startswith("bgp"):
                            create_payload = parcel_builder.dict()
                            create_url = parcel_builder.create_api_url().format(transportId=profile_id)
                            # Get the BGP name for better logging and tracking
                            bgp_name = parcel_builder.name if hasattr(parcel_builder, 'name') else key
                            resp_bgp_json, _ = _log_and_post(session, "Create BGP Parcel", bgp_name, create_url, create_payload, parent_profile=profile_name)
                            bgp_id = resp_bgp_json.get('parcelId')
                            if bgp_id:
                                assoc_payload = {"parcelId": bgp_id}
                                associate_url = parcel_builder.associate_api_url().format(transportId=profile_id, vpnId=vpn_id)
                                # Debug logging
                                logging.info(f"About to associate BGP Parcel: bgp_id={bgp_id}, payload={assoc_payload}")
                                # Make the API call
                                assoc_resp, _ = _log_and_post(session, "Associate BGP Parcel", bgp_name, associate_url, assoc_payload, parent_profile=f"{profile_name}.{actual_vpn_name}")
                                # Debug the response
                                logging.info(f"BGP Association response: {assoc_resp}")
                return
            # --- Generic handling for System profile ---
            elif prf_type == "System":
                for key, parcel_builder in parcel_builders.items():
                    if parcel_builder:
                        parcel_payload = parcel_builder.dict()
                        parcel_api_url = parcel_builder.api_url().format(systemId=profile_id)
                        _log_and_post(session, f"Create System Parcel", key, parcel_api_url, parcel_payload, parent_profile=profile_name)
                return
    except Exception as e:
        logging.error(f"An unhandled error occurred in post_vmanager: {e}")
        sys.exit(e)

def sys_profile_builders():
    """
    Function to read the Excel file generate json payloads for vManager
    to configurate System Profile and other parcels.
    """
    # Read the Excel file
    #df = pd.read_excel('input.xlsx', sheet_name='system')

    df = pd.read_excel('input.xlsx', sheet_name='system', dtype={
        'value': str,  # Force pandas to read all values as strings
        'fieldName': str,
        'optionType': str,
        'section': str
    })

    # Create SysProfileBuilder from DataFrame
    sys_profile_builder = parse_excel_to_sys_profile_builder(df)
    builders_map = {
        "global": parse_excel_to_global_builder,
        "aaa": parse_excel_to_aaa_builder,
        "bfd": parse_excel_to_bfd_builder,
        "omp": parse_excel_to_omp_builder,
        "basic": parse_excel_to_basic_builder,
        "banner": parse_excel_to_banner_builder,
        "ntp": parse_excel_to_ntp_builder,
        "logg": parse_excel_to_logg_builder,
        "snmp": parse_excel_to_snmp_builder,
        "security": parse_excel_to_security_builder,
    }

    sys_builders = {}
    for key, func in builders_map.items():
        sys_builders[key] = func(df)

    return sys_profile_builder, sys_builders


def transport_profile_builders():
    """
    Function to read the Excel file generate json payloads for vManager
    to configurate Transport Profile and other parcels.
    """
    # Read the Excel file
    #df = pd.read_excel('input.xlsx', sheet_name='transport')

    df = pd.read_excel('input.xlsx', sheet_name='transport', dtype={
        'value': str,  # Force pandas to read all values as strings
        'fieldName': str,
        'optionType': str,
        'section': str
    })

    # Create transportProfileBuilder from DataFrame
    transport_profile_builder = parse_excel_to_transport_profile_builder(df)

    builders_map = {
        "vpn": parse_excel_to_vpn_builder,
        "interface": parse_excel_to_interface_builders,
        "bgp": parse_excel_to_bgp_builder,
    }

    transport_builders = {}
    for key, func in builders_map.items():
        result = func(df)
        if key == "vpn":
            # Handle multiple VPN builders if returned as a list
            if isinstance(result, list):
                for i, builder in enumerate(result):
                    transport_builders[f"{key}_{i}"] = builder
            else:
                transport_builders[key] = result
        elif key == "interface":
            # Handle multiple interface builders
            for i, builder in enumerate(result):
                transport_builders[f"{key}_{i}"] = builder
        elif key == "bgp":
            transport_builders[key] = result

    return transport_profile_builder, transport_builders


def service_profile_builders():
    """
    Function to read the Excel file generate json payloads for vManager
    to configurate Service Profile and other parcels.
    """
    # Read the Excel file
    df = pd.read_excel('input.xlsx', sheet_name='service', dtype={
        'ObjectName': str,
        'Type': str,
        'Name': str,
        'Description': str,
        'parent1': str,
        'parent2': str,
        'section': str,
        'fieldName': str,
        'optionType': str,
        'value': str
    })

    # Create serviceProfileBuilder from DataFrame
    service_profile_builders_list = parse_excel_to_service_profile_builders(df)

    # Create a dictionary of VPN builders keyed by their parent service profile
    vpn_builders_by_parent = parse_excel_to_service_vpn_builders(df)

    # Create a dictionary of Interface builders keyed by their parent (service_profile, vpn_name)
    interface_builders_by_parent = parse_excel_to_service_interface_builders(df)

    return service_profile_builders_list, vpn_builders_by_parent, interface_builders_by_parent


def cli_profile_builders():
    """
    Function to read the Excel file and generate CLI Main Profile and CLI Profile builders.
    Returns:
        tuple: (main_profile_builders, cli_profile_builders)
    """
    df = pd.read_excel('input.xlsx', sheet_name='cli', dtype={
        'ObjectName': str,
        'Type': str,
        'Name': str,
        'Description': str,
        'Config': str
    })
    main_profile_builders = parse_excel_to_cli_profiles_builder(df)
    cli_profile_builders = parse_excel_to_cli_builder(df)
    return main_profile_builders, cli_profile_builders


def configuration_group_builders():
    """
    Function to read the Excel file and generate configuration group builders.
    Config groups reference other profiles by ID, which need to be fetched or looked up.
    
    This function attempts to resolve profile names to IDs from the objects_created.xlsx file.
    It also resolves the deviceX.unsupportedFeatures names to their corresponding IDs.
    
    The function handles three formats for unsupportedFeatures:
    1. Simple strings with feature names (e.g., "Branch_WAN.vpn_0.interface_5")
    2. List of dictionaries with 'parcelType' and 'parcelId' keys
    3. Custom string format '["parcelType": "featureId", "parcelType": "featureId"]'
    
    Returns:
        A list of ConfigGroupBuilder objects ready to be converted to API payloads
    """
    # Read the Excel file for configuration groups
    input_df = pd.read_excel('input.xlsx', sheet_name='ConfGroups')
    
    # Try to read the objects_created.xlsx to get profile and feature IDs
    try:
        objects_df = pd.read_excel('objects_created.xlsx')
        # Create a mapping from profile name to ID
        profile_id_map = {}
        
        # Helper to normalize profile names for mapping
        def normalize_profile_name(name):
            return str(name).replace('-', '').replace('_', '').replace(' ', '').lower()

        # Extract profile names and IDs from the objects_created.xlsx file using the Name column
        for _, row in objects_df.iterrows():
            # Skip rows without Name or ID
            if 'Name' not in row or 'ID' not in row or pd.isna(row['Name']) or pd.isna(row['ID']):
                continue
                
            name = str(row['Name'])
            object_id = row['ID']
            object_type = row.get('Object Type', '')
            object_url = row.get('URL', '')
            
            # Map the profile by its exact name
            profile_id_map[normalize_profile_name(name)] = {
                'id': object_id,
                'url': object_url,
                'type': object_type
            }
            
            # Also map profiles by their type for generic lookups
            # Only map top-level profiles (those without dots in their name)
            if '.' not in name and object_type:
                if object_type == 'System':
                    profile_id_map[normalize_profile_name("system")] = {
                        'id': object_id,
                        'url': object_url,
                        'type': object_type
                    }
                elif object_type == 'Service':
                    profile_id_map[normalize_profile_name("service")] = {
                        'id': object_id,
                        'url': object_url,
                        'type': object_type
                    }
                elif object_type == 'Transport':
                    profile_id_map[normalize_profile_name("transport")] = {
                        'id': object_id,
                        'url': object_url,
                        'type': object_type
                    }
                elif object_type == 'CLI':
                    profile_id_map[normalize_profile_name("cli")] = {
                        'id': object_id,
                        'url': object_url,
                        'type': object_type
                    }
                    json_logger.debug(f"Mapped CLI Profile '{name}' to ID {object_id}")
                    
            json_logger.debug(f"Added mapping: {name} -> {object_id} (Type: {object_type})")
        
        json_logger.debug(f"Profile ID mapping: {profile_id_map}")
        logging.info(f"Found {len(profile_id_map)} profile IDs in objects_created.xlsx")
        
        # Replace profile names with IDs in the input DataFrame
        import re
        uuid_re = re.compile(r"^[0-9a-fA-F-]{36}$")
        
        # Get list of columns to process for profiles
        profile_columns = [col for col in ['system', 'transport', 'service', 'policy', 'cli', 'uc', 'other'] 
                           if col in input_df.columns]
        logging.info(f"Processing profile references in columns: {', '.join(profile_columns)}")
        
        # Process each profile column
        for col in profile_columns:
            json_logger.debug(f"Checking column '{col}' for profile references")
            for idx, value in input_df[col].items():
                if pd.notna(value):
                    # If value is already a UUID, keep it
                    if isinstance(value, str) and uuid_re.match(value):
                        continue
                    norm_value = normalize_profile_name(value)
                    json_logger.debug(f"Looking for mapping for '{value}' (normalized: '{norm_value}') in column '{col}'")
                    
                    if norm_value in profile_id_map:
                        input_df.at[idx, col] = profile_id_map[norm_value]['id']
                        json_logger.debug(f"SUCCESS: Replaced profile name '{value}' with ID '{profile_id_map[norm_value]['id']}'")
                    else:
                        logging.warning(f"FAILED: Profile reference '{value}' in column '{col}' could not be mapped to a UUID. This may cause API errors.")
        
        # Process device unsupported features columns
        device_idx = 1
        while f"device{device_idx}.Tag" in input_df.columns and f"device{device_idx}.unsupportedFeatures" in input_df.columns:
            unsupported_col = f"device{device_idx}.unsupportedFeatures"
            logging.info(f"Processing device{device_idx} unsupported features")
            
            # For each row in the dataframe
            for idx, value in input_df[unsupported_col].items():
                if pd.notna(value):
                    # Parse the value to ensure it's a list
                    if isinstance(value, str):
                        try:
                            # Special handling for the custom format with parcel types and IDs
                            if '"' in value and ':' in value and value.startswith('[') and value.endswith(']'):
                                # This could be our custom format: '["parcelType": "id", "parcelType": "id"]'
                                import re
                                pattern = r'"([^"]+)":\s*"([^"]+)"'
                                matches = re.findall(pattern, value)
                                
                                if matches:
                                    # Each match is (parcel_type, feature_name)
                                    # We need to transform this into a list of feature names
                                    value = [feature_name for _, feature_name in matches]
                                else:
                                    # Fall back to standard parsing if regex didn't match
                                    import ast
                                    try:
                                        # Try to parse as Python literal
                                        value = ast.literal_eval(value)
                                    except:
                                        # If it's just a single string, make it a single-item list
                                        value = [value]
                            elif value.startswith('[') and value.endswith(']'):
                                # Try to parse as Python literal if it looks like a standard list
                                import ast
                                try:
                                    value = ast.literal_eval(value)
                                except:
                                    # If parsing fails, keep as a single-item list
                                    value = [value]
                            else:
                                # If it's just a single string, make it a single-item list
                                value = [value]
                        except:
                            # If all parsing fails, keep as a single-item list
                            value = [value]
                    elif not isinstance(value, list):
                        value = [value]
                    
                    # For each feature name in the list, look up the corresponding ID
                    mapped_features = []
                    for feature_name in value:
                        if not feature_name or pd.isna(feature_name):
                            continue
                            
                        feature_name_str = str(feature_name)
                        norm_feature = normalize_profile_name(feature_name_str)
                        
                        if norm_feature in profile_id_map:
                            feature_data = profile_id_map[norm_feature]
                            feature_id = feature_data['id']
                            feature_url = feature_data['url']
                            
                            # Extract parcel type from URL
                            url_parts = feature_url.split('/')
                            parcel_type = ""
                            
                            if 'feature-profile' in url_parts and len(url_parts) >= 9:
                                # Extract the parcel type part
                                parcel_type_parts = []
                                for i in range(7, len(url_parts)-1):
                                    if url_parts[i] and not uuid_re.match(url_parts[i]):
                                        parcel_type_parts.append(url_parts[i])
                                
                                # Join to form parcelType like "wan/vpn/interface/ethernet"
                                parcel_type = '/'.join(parcel_type_parts)
                                
                                # Create the structure needed for unsupportedFeatures
                                mapped_features.append({
                                    "parcelType": parcel_type,
                                    "parcelId": feature_id
                                })
                                
                                json_logger.debug(f"Mapped unsupported feature '{feature_name}' to ID {feature_id} with type {parcel_type}")
                            else:
                                logging.warning(f"Could not extract parcelType from URL: {feature_url}")
                                # Use a default structure with just the ID
                                mapped_features.append({
                                    "parcelType": "wan/vpn/interface/ethernet",
                                    "parcelId": feature_id
                                })
                        else:
                            logging.warning(f"Could not find ID for unsupported feature '{feature_name}' in objects_created.xlsx")
                            # If we can't map it, keep the original value
                            mapped_features.append({
                                "parcelType": "wan/vpn/interface/ethernet",
                                "parcelId": feature_name_str
                            })
                    
                    # Update the dataframe with the mapped features
                    input_df.at[idx, unsupported_col] = mapped_features
                    json_logger.debug(f"Updated device{device_idx} unsupported features: {mapped_features}")
            
            device_idx += 1
                    
    except Exception as e:
        logging.warning(f"Could not read profile IDs from objects_created.xlsx: {e}")
        logging.warning("Profile names will be used as-is. Make sure they are already IDs.")
    
    # Parse the DataFrame into ConfigGroupBuilder objects
    config_group_builders_list = parse_excel_to_config_group_builders(input_df)
    logging.info(f"Created {len(config_group_builders_list)} config group builders")
    
    # Validate UUID format for profile references (log details only to debug file)
    import json
    for builder in config_group_builders_list:
        # Check if all profiles are UUIDs
        profiles = builder._model.profiles or []
        for prof in profiles:
            prof_id = getattr(prof, 'id', None)
            if prof_id and not (isinstance(prof_id, str) and len(prof_id) == 36 and '-' in prof_id):
                logging.warning(f"ConfigGroupBuilder '{builder.name}' has a profile reference that does not look like a UUID: {prof_id}")
        
        # Log the payload to debug file only
        payload_json = json.dumps(builder.dict(), indent=2)
        json_logger.debug(f"ConfigGroupBuilder: {builder.name} | Payload:\n{payload_json}")
    
    return config_group_builders_list


def track_created_object(object_type, parcel_type, action, object_name):
    """
    Track an object created during the current execution for summary purposes.
    """
    # Create nested dictionary structure if it doesn't exist
    if object_type not in current_run_summary:
        current_run_summary[object_type] = {}
    
    if parcel_type not in current_run_summary[object_type]:
        current_run_summary[object_type][parcel_type] = 0
    
    # Increment the counter
    current_run_summary[object_type][parcel_type] += 1


def print_execution_summary():
    """
    Print a summary of all objects created during this execution.
    """
    if not current_run_summary:
        logging.info("No objects were created during this execution.")
        return
    
    # Calculate total objects
    total_objects = sum(sum(parcels.values()) for parcels in current_run_summary.values())
    
    logging.info("=" * 70)
    logging.info("EXECUTION SUMMARY")
    logging.info("=" * 70)
    logging.info(f"Total objects created: {total_objects}")
    logging.info("")
    
    # Define the desired order for object types
    desired_order = ['ConfigGroup', 'System', 'Transport', 'Policy', 'Service', 'CLI']
    
    # Create a list of object types in the desired order, including any not in the predefined list
    ordered_types = []
    for obj_type in desired_order:
        if obj_type in current_run_summary:
            ordered_types.append(obj_type)
    
    # Add any remaining types that aren't in the predefined order (alphabetically sorted)
    remaining_types = sorted([t for t in current_run_summary.keys() if t not in desired_order])
    ordered_types.extend(remaining_types)
    
    # Print detailed breakdown by object type and parcel type in the specified order
    for obj_type in ordered_types:
        type_total = sum(current_run_summary[obj_type].values())
        logging.info(f"{obj_type}: {type_total} objects")
        
        # Sort parcel types for consistent output
        for parcel_type in sorted(current_run_summary[obj_type].keys()):
            count = current_run_summary[obj_type][parcel_type]
            logging.info(f"  ├─ {parcel_type}: {count}")
    
    logging.info("")
    logging.info(f"All objects saved to: objects_created.xlsx")
    logging.info("=" * 70)


def save_created_objects_to_excel(filename="objects_created.xlsx"):
    """
    Save the list of created objects to an Excel file.
    Appends to the existing file if it exists, otherwise creates a new file.
    Prevents duplicate entries using ID and Run ID as unique keys.
    
    Args:
        filename (str): The name of the Excel file to create or append to
    """
    # Track which objects have been saved in this run
    if not hasattr(save_created_objects_to_excel, 'saved_object_ids'):
        save_created_objects_to_excel.saved_object_ids = set()
        
    json_logger.debug(f"save_created_objects_to_excel: {len(created_objects)} objects available to save")
    
    # Extract object type from the URL, which is more consistent
    for obj in created_objects:
        if 'URL' in obj and 'Object Name' in obj:
            url = obj['URL']
            object_name = obj['Object Name']
            
            # Extract name from Object Name and URL
            name = ""
            
            # Parse the object name to get a better name with hierarchical dot notation
            
            # 1. First handle profile objects (top level)
            if "Profile for " in object_name and "'" not in object_name:
                # Extract profile name (e.g., "system-profile-rnsi")
                if "System Profile for " in object_name:
                    name = object_name.replace("Create System Profile for ", "")
                elif "Transport Profile for " in object_name:
                    name = object_name.replace("Create Transport Profile for ", "")
                elif "Service Profile for " in object_name:
                    name = object_name.replace("Create Service Profile for ", "")
                elif "CLI Profile for " in object_name:
                    name = object_name.replace("Create CLI Profile for ", "")
                elif "ConfigGroup Profile for " in object_name:
                    name = object_name.replace("Create ConfigGroup Profile for ", "")
                else:
                    name = object_name.split(" for ")[-1]
                    if " of Profile" in name:
                        name = name.split(" of Profile")[0]
                        
            # 1.5. Handle System, Transport and other parcels with parent info
            elif " Parcel for " in object_name and " in " in object_name and "'" not in object_name:
                # Format: "Create System Parcel for global in system-profile-rnsi"
                parts = object_name.split(" for ")
                if len(parts) >= 2:
                    parcel_info = parts[1]
                    # Extract parcel name and parent profile
                    if " in " in parcel_info:
                        parcel_name = parcel_info.split(" in ")[0].strip()
                        parent_name = parcel_info.split(" in ")[1].strip()
                        name = f"{parent_name}.{parcel_name}"
                    else:
                        name = parcel_info
            
            # 1.6. Handle CLI Config specially
            elif "Create CLI Config for " in object_name:
                # Format: "Create CLI Config for for profile cli-add-on"
                profile_part = object_name.replace("Create CLI Config for for profile ", "")
                if profile_part:
                    name = f"{profile_part}.config"
            
            # 2. Handle VPN parcels (second level)
            elif "VPN Parcel '" in object_name:
                # Extract: VPN name and profile name
                vpn_name = None
                profile_name = None
                
                # Get the VPN name between quotes
                quoted_parts = object_name.split("'")
                if len(quoted_parts) >= 3:
                    vpn_name = quoted_parts[1]
                
                # Get the profile name
                if " for in " in object_name:
                    # Format: "Create VPN Parcel 'RMANEPC' for in SP-ANEPC_MS"
                    profile_part = object_name.split(" for in ")
                    if len(profile_part) >= 2:
                        profile_name = profile_part[1].strip()
                        # Clean up profile name
                        if " of Profile " in profile_name:
                            profile_name = profile_name.split(" of Profile ")[0]
                        if "'" in profile_name:
                            profile_name = profile_name.replace("'", "").strip()
                            
                # Create dot notation
                if profile_name and vpn_name:
                    name = f"{profile_name}.{vpn_name}"
                else:
                    name = vpn_name or "Unknown VPN"
            
            # 3. Handle Interface parcels (third level)
            elif "Interface Parcel '" in object_name:
                # Extract: Interface name, VPN name, and profile name
                # Format: "Create Interface Parcel 'Interface-RMMS_VLAN751' for in VPN 'RMMS' of Profile 'SP-ANEPC_MS'"
                interface_name = None
                vpn_name = None
                profile_name = None
                
                # Get the interface name between the first set of quotes
                quoted_parts = object_name.split("'")
                if len(quoted_parts) >= 3:
                    interface_name = quoted_parts[1]
                
                # Extract VPN and Profile information
                if " for in VPN '" in object_name and "' of Profile '" in object_name:
                    # This is the full format with VPN and Profile information
                    vpn_part = object_name.split(" for in VPN '")[1]
                    if "' of Profile '" in vpn_part:
                        vpn_name = vpn_part.split("' of Profile '")[0]
                        profile_name = vpn_part.split("' of Profile '")[1].strip("'")
                
                # Handle cases where format might be different
                if not vpn_name and len(quoted_parts) >= 5 and "VPN '" in object_name:
                    vpn_name = quoted_parts[3]
                
                if not profile_name and len(quoted_parts) >= 7 and "Profile '" in object_name:
                    profile_name = quoted_parts[5]
                
                # Create dot notation hierarchy
                if profile_name and vpn_name and interface_name:
                    name = f"{profile_name}.{vpn_name}.{interface_name}"
                elif vpn_name and interface_name:
                    name = f"Unknown.{vpn_name}.{interface_name}"
                else:
                    name = interface_name or "Unknown Interface"
                    
            # 4. Handle BGP parcels and associations specifically
            elif "BGP Parcel" in object_name:
                # First determine if it's a create or associate action
                is_associate = object_name.startswith("Associate BGP Parcel")
                
                if is_associate:
                    # Format: "Associate BGP Parcel for <key> in <profile_name>.<vpn_name>"
                    if " for " in object_name and " in " in object_name:
                        # Get the "key" part after "for"
                        key_part = object_name.split(" for ")[1].split(" in ")[0].strip()
                        # Get the hierarchy after "in"
                        hierarchy = object_name.split(" in ")[1].strip()
                        # Create the name with an "Association" indicator
                        name = f"{hierarchy}.BGP-{key_part}.Association"
                else:
                    # Format: "Create BGP Parcel for <key> in <profile_name>"
                    if " for " in object_name and " in " in object_name:
                        # Get the "key" part after "for"
                        key_part = object_name.split(" for ")[1].split(" in ")[0].strip()
                        # Get the profile part after "in"
                        profile_part = object_name.split(" in ")[1].strip()
                        # Create the name
                        name = f"{profile_part}.BGP-{key_part}"
                    elif " for " in object_name:
                        # Simpler format without "in"
                        key_part = object_name.split(" for ")[1].strip()
                        name = f"BGP-{key_part}"
            
            # 5. Handle other parcel types (System parcels, etc.)
            elif " Parcel for " in object_name:
                parcel_type = object_name.split(" Parcel for ")[0].split("Create ")[-1]
                parcel_name = object_name.split(" Parcel for ")[-1]
                
                # Handle case where it's a simple parcel name
                if " of " not in parcel_name:
                    name = parcel_name
                else:
                    # It's more complex, try to form a hierarchical name
                    parent_name = None
                    if " of Profile " in parcel_name:
                        parts = parcel_name.split(" of Profile ")
                        if len(parts) >= 2:
                            parent_name = parts[1].strip("'")
                            parcel_name = parts[0].strip()
                            name = f"{parent_name}.{parcel_name}"
                    else:
                        name = parcel_name
            
            # 5. Generic extraction for other cases
            elif "'" in object_name and " for " in object_name:
                # Extract the quoted name
                quoted_parts = object_name.split("'")
                if len(quoted_parts) >= 3:
                    name = quoted_parts[1]
                    
                    # Try to get context from the "for" part
                    for_parts = object_name.split(" for ")
                    if len(for_parts) >= 2:
                        context = for_parts[1]
                        if context and context != name:
                            name = f"{context}.{name}"
            
            # 6. Fallback to simple extraction
            elif not name and " for " in object_name:
                name = object_name.split(" for ")[-1]
                if " of Profile" in name:
                    name = name.split(" of Profile")[0]
                    
            # 7. Special handling for config groups and CLI config
            elif "ConfigGroup Profile for " in object_name:
                name = object_name.replace("Create ConfigGroup Profile for ", "")
            elif "CLI Config for " in object_name:
                # Format: "Create CLI Config for profile cli-add-on"
                # Format: "Create CLI Config for for profile cli-add-on"
                if "profile " in object_name:
                    profile_name = object_name.split("profile ")[1].strip()
                    name = f"{profile_name}.config"
                elif "for profile " in object_name:
                    profile_name = object_name.split("for profile ")[1].strip()
                    name = f"{profile_name}.config"
                
            # Add name field
            obj['Name'] = name
            
            # Debug log the name extraction for easier troubleshooting
            json_logger.debug(f"Extracted name '{name}' from Object Name '{object_name}'")
            
            # Extract Object Type based on URL path components and object name
            # Special handling for BGP associations
            if "Associate BGP Parcel" in object_name:
                obj['Object Type'] = 'Transport-Association'
            elif '/system' in url:
                obj['Object Type'] = 'System'
            elif '/transport' in url:
                obj['Object Type'] = 'Transport'
            elif '/service' in url:
                obj['Object Type'] = 'Service'
            elif '/cli' in url:
                obj['Object Type'] = 'CLI'
            elif '/config-group' in url:
                obj['Object Type'] = 'ConfigGroup'
            else:
                obj['Object Type'] = 'Unknown'
    
    # Filter for objects that haven't been saved yet
    new_objects_to_save = []
    for obj in created_objects:
        # Create a unique key for this object
        obj_id = obj.get('ID', '')
        obj_run_id = obj.get('Run ID', '')
        unique_key = f"{obj_id}_{obj_run_id}"
        
        if unique_key not in save_created_objects_to_excel.saved_object_ids:
            json_logger.debug(f"Object to save: {obj}")
            new_objects_to_save.append(obj)
            save_created_objects_to_excel.saved_object_ids.add(unique_key)
    
    if not new_objects_to_save:
        # Silent operation - don't log when no new objects to save
        return
        
    try:
        # Create DataFrame from the filtered objects
        new_df = pd.DataFrame(new_objects_to_save)
        
        # Define column order for better readability
        columns = [
            'Run ID',        
            'Timestamp',     
            'Object Type',   
            'Name',          
            'Object Name',   
            'URL',           
            'ID',            
        ]
        
        # Check if the file already exists
        file_exists = Path(filename).exists()
        
        if file_exists:
            # Read existing file and append new data
            try:
                existing_df = pd.read_excel(filename)
                            
                # Combine the existing and new data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # Reorder columns and handle missing columns
                available_columns = [col for col in columns if col in combined_df.columns]
                other_columns = [col for col in combined_df.columns if col not in columns]
                final_columns = available_columns + other_columns
                
                # Explicitly reorder the DataFrame columns before saving
                combined_df = combined_df[final_columns]
                
                # Save to Excel with ordered columns
                combined_df.to_excel(filename, index=False)
                
                # Silent operation - no individual save logging
            except Exception as e:
                logging.warning(f"Failed to read existing Excel file: {e}. Creating a new file.")
                # If there's an issue with the existing file, create a new one
                available_columns = [col for col in columns if col in new_df.columns]
                other_columns = [col for col in new_df.columns if col not in columns]
                final_columns = available_columns + other_columns
                
                # Explicitly reorder the DataFrame columns before saving
                new_df = new_df[final_columns]
                
                new_df.to_excel(filename, index=False)
                # Silent operation - no individual save logging
        else:
            # Create a new Excel file if it doesn't exist
            available_columns = [col for col in columns if col in new_df.columns]
            other_columns = [col for col in new_df.columns if col not in columns]
            final_columns = available_columns + other_columns
            
            # Explicitly reorder the DataFrame columns before saving
            new_df = new_df[final_columns]
            
            new_df.to_excel(filename, index=False)
            
            # Count objects by type for better reporting
            type_counts = {}
            for obj_type in new_df['Object Type'].unique():
                count = len(new_df[new_df['Object Type'] == obj_type])
                type_counts[obj_type] = count
            
            # Create a summary string
            type_summary = ", ".join([f"{count} {obj_type}" for obj_type, count in type_counts.items()])
            
            logging.info(f"Successfully saved list of {len(new_df)} created objects to {filename}")
            logging.info(f"Objects by type: {type_summary}")
            
    except Exception as e:
        logging.error(f"Failed to save created objects to Excel: {e}")


# Main execution
if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Create configurations on vManager from Excel data')
    parser.add_argument('--feature-type', type=str, help='Comma-separated list of feature types to process (system,transport,service,cli,config-groups). If not specified, all feature types will be processed in order.')
    args = parser.parse_args()
    
        # Determine which feature types to process
    feature_types = []
    if args.feature_type:
        feature_types = [ft.strip().lower() for ft in args.feature_type.split(',')]
        logging.info(f"Processing feature types: {feature_types}")
    else:
        # Default to all feature types if none specified
        feature_types = ['system', 'transport', 'service', 'cli', 'config-groups']
    
    try:
        # Process system profile if requested
        if 'system' in feature_types:
            try:
                system_profile_builder, system_builders = sys_profile_builders()
                if system_profile_builder:
                    post_vmanager("System", url, username, password, system_profile_builder, system_builders)
                    save_created_objects_to_excel()
            except Exception as e:
                logging.error(f"Error in system profile processing: {e}")
                save_created_objects_to_excel()
                if 'system' == feature_types[-1]:  # If this was the last feature type, raise to exit
                    raise

        # Process transport profile if requested
        if 'transport' in feature_types:
            try:
                transport_profile_builder, transport_builders = transport_profile_builders()
                if transport_profile_builder:
                    post_vmanager("Transport", url, username, password, transport_profile_builder, transport_builders)
                    save_created_objects_to_excel()
            except Exception as e:
                logging.error(f"Error in transport profile processing: {e}")
                save_created_objects_to_excel()
                if 'transport' == feature_types[-1]:  # If this was the last feature type, raise to exit
                    raise

        # Process service profile if requested
        if 'service' in feature_types:
            try:
                service_profile_builders_list, service_builders, interface_builders = service_profile_builders()
                if service_profile_builders_list:
                    post_vmanager("Service", url, username, password, service_profile_builders_list, service_builders, interface_builders)
                    save_created_objects_to_excel()
            except Exception as e:
                logging.error(f"Error in service profile processing: {e}")
                save_created_objects_to_excel()
                if 'service' == feature_types[-1]:  # If this was the last feature type, raise to exit
                    raise
        
        # Process CLI profile if requested
        if 'cli' in feature_types:
            try:
                main_profile_builders, cli_profile_builders_list = cli_profile_builders()
                if main_profile_builders:
                    post_vmanager("CLI", url, username, password, main_profile_builders, cli_profile_builders_list)
                    save_created_objects_to_excel()
            except Exception as e:
                logging.error(f"Error in CLI profile processing: {e}")
                save_created_objects_to_excel()
                if 'cli' == feature_types[-1]:  # If this was the last feature type, raise to exit
                    raise
        
        # Process configuration groups if requested
        if 'config-groups' in feature_types:
            try:
                config_group_builders_list = configuration_group_builders()
                if config_group_builders_list:
                    post_vmanager("config-group", url, username, password, config_group_builders_list, parcel_builders=None)
                    save_created_objects_to_excel()
            except Exception as e:
                logging.error(f"Error in config groups processing: {e}")
                save_created_objects_to_excel()
                if 'config-groups' == feature_types[-1]:  # If this was the last feature type, raise to exit
                    raise
        
        # Save the created objects to Excel (final backup)
        save_created_objects_to_excel()
        
        # Print execution summary
        print_execution_summary()
    except Exception as e:
        logging.error(f"An error occurred during execution: {e}")
        # Still try to save any objects that were created before the error
        save_created_objects_to_excel()
        
        # Print summary even if there was an error
        print_execution_summary()
