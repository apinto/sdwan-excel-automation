from .profile import ServiceProfileBuilder
from .vpn import VpnBuilder
from .interface import ServiceInterfaceBuilder
import pandas as pd
import logging
import re
from typing import Dict, List


def parse_value(raw):
    """
    Custom parser for Excel cell values.
    - Handles None/NaN values.
    - Converts "TRUE" or "true" (case-insensitive) to Python boolean True.
    - Converts "FALSE" or "false" (case-insensitive) to Python boolean False.
    - Splits comma-separated strings into a list of strings.
    - Tries to convert standalone numeric strings to int or float.
    - Otherwise, returns the value as a stripped string.
    """
    if pd.isna(raw):
        return None
    
    # Ensure we're working with a string representation for consistent processing
    val_str = str(raw).strip()

    # Handle boolean conversion first
    if val_str.lower() == 'true':
        return True
    if val_str.lower() == 'false':
        return False

    # Handle comma-separated lists
    if ',' in val_str:
        return [v.strip() for v in val_str.split(',')]

    # Handle numeric conversion for values that are purely numeric
    if val_str.isdigit():
        return int(val_str)
    try:
        # This will handle floating point numbers
        return float(val_str)
    except (ValueError, TypeError):
        # If all conversions fail, return the original string
        return val_str

def extract_field(row, field_name):
    return str(row[field_name]).strip() if not pd.isna(row[field_name]) else None

def parse_excel_to_service_profile_builders(df) -> List[ServiceProfileBuilder]:
    ''' returns a list of ServiceProfileBuilder instances based on the DataFrame input '''
    builders = []
    for _, row in df.iterrows():
        if row['ObjectName'] == 'Service Profile' and row['Type'] == 'main':
            name = str(row['Name']).strip()
            description = str(row['Description']).strip()
            builder = ServiceProfileBuilder(name=name, description=description)
            builders.append(builder)
            logging.getLogger('json_payload').info(f"Service Profile json payload for {name}: {builder.json()}")
    return builders

def parse_excel_to_service_vpn_builders(df: pd.DataFrame) -> Dict[str, List[VpnBuilder]]:
    """
    Parses a DataFrame and returns a dictionary mapping service profile names
    to a list of their associated VpnBuilder instances.
    """
    vpn_builders: Dict[tuple[str, str], VpnBuilder] = {}

    # Filter for rows that define VPN parcels
    vpn_df = df[df['Type'].str.strip().str.lower() == 'vpn'].copy()
    
    for _, row in vpn_df.iterrows():
        parent_service = extract_field(row, 'parent1')
        vpn_name = extract_field(row, 'Name')
        vpn_description = extract_field(row, 'Description')
        
        if not parent_service or not vpn_name:
            continue

        builder_key = (parent_service, vpn_name)

        # Get or create the builder
        if builder_key not in vpn_builders:
            # Find the initial vpnId for this VPN to initialize the builder
            vpn_id_row = vpn_df[
                (vpn_df['parent1'] == parent_service) &
                (vpn_df['Name'] == vpn_name) &
                (vpn_df['fieldName'] == 'vpnId')
            ]
            if not vpn_id_row.empty:
                vpn_id = int(float(vpn_id_row.iloc[0]['value']))
                vpn_builders[builder_key] = VpnBuilder(name=vpn_name, description=vpn_description, vpn_id=vpn_id)
            else:
                # Cannot create a builder without a vpnId, skip all rows for this VPN
                logging.warning(f"Could not find vpnId for VPN '{vpn_name}' under service '{parent_service}'. Skipping.")
                continue
        
        builder = vpn_builders[builder_key]

        # Set the attribute for the current row
        section = extract_field(row, 'section')
        field_name = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        raw_value = row['value']
        
        # Skip setting the vpnId again as it's used for initialization
        if field_name == 'vpnId':
            continue

        value = parse_value(raw_value)

        logging.debug(f"Processing VPN '{vpn_name}': section='{section}', field='{field_name}', value='{value}'")
        try:
            builder.set_path_option(section, field_name, option_type, value)
        except Exception:
            import traceback
            logging.error(f"Failed to set path for VPN '{vpn_name}': section='{section}', field='{field_name}'")
            logging.error(traceback.format_exc())


    # Restructure the dictionary for the final output
    final_builders: Dict[str, List[VpnBuilder]] = {}
    for (parent, _), builder in vpn_builders.items():
        if parent not in final_builders:
            final_builders[parent] = []
        final_builders[parent].append(builder)
        logging.getLogger('json_payload').info(f"VPN Parcel for '{builder._model.name}' under '{parent}' JSON payload: {builder.json()}")

    return final_builders


def parse_excel_to_service_interface_builders(df: pd.DataFrame) -> Dict[tuple[str, str], list[ServiceInterfaceBuilder]]:
    """
    Parses a DataFrame and returns a dictionary mapping (service_profile_name, vpn_name)
    to a list of their associated ServiceInterfaceBuilder instances.
    """
    interface_builders: dict[tuple[str, str, str], ServiceInterfaceBuilder] = {}

    # Filter for rows that define interface subparcels
    interface_df = df[df['Type'].str.strip().str.lower() == 'interface'].copy()

    for _, row in interface_df.iterrows():
        service_profile = extract_field(row, 'parent1')
        vpn_name = extract_field(row, 'parent2')
        interface_name = extract_field(row, 'Name')
        description = extract_field(row, 'Description')

        if not all([service_profile, vpn_name, interface_name]):
            logging.warning(f"Skipping row with missing parent/name information: {row.to_dict()}")
            continue

        builder_key = (service_profile, vpn_name, interface_name)

        # Get or create the builder for the specific interface
        if builder_key not in interface_builders:
            interface_builders[builder_key] = ServiceInterfaceBuilder(name=interface_name, description=description)
        
        builder = interface_builders[builder_key]

        # Set the attribute for the current row
        section = extract_field(row, 'section')
        field_name = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        raw_value = row['value']
        
        if pd.isna(raw_value):
            continue

        value = parse_value(raw_value)
        
        # Combine section and fieldName to create the path, handling 'interface_root'
        path = f"{section}.{field_name}" if section and section != 'interface_root' else field_name

        logging.debug(f"Processing Interface '{interface_name}': path='{path}', value='{value}', option='{option_type}'")
        try:
            builder.set_path_option(path, value, option_type)
        except Exception:
            import traceback
            logging.error(f"Failed to set path for Interface '{interface_name}': path='{path}', value='{value}'")
            logging.error(traceback.format_exc())

    # Restructure the dictionary for the final output, grouping interfaces by (service, vpn)
    final_builders: dict[tuple[str, str], list[ServiceInterfaceBuilder]] = {}
    for (service, vpn, name), builder in interface_builders.items():
        key = (service, vpn)
        if key not in final_builders:
            final_builders[key] = []
        final_builders[key].append(builder)
        logging.getLogger('json_payload').info(f"Interface Parcel for '{name}' under {key} JSON payload: {builder.json()}")

    return final_builders
