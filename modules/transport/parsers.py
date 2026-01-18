from .profile import transportProfileBuilder
from .vpn import VpnBuilder
from .interface import InterfaceBuilder
from .bgp import BGPBuilder

import pandas as pd

import logging
#from collections import defaultdict
#import re

def parse_value(raw):
    if pd.isna(raw):
        return None
    if isinstance(raw, str):
        if "," in raw:
            return [v.strip() for v in raw.split(",")]
        elif raw.lower() in ["true", "false"]:
            return raw.lower() == "true"
        else:
            # tries to convert to int or float
            try:
                if '.' in raw:
                    return float(raw)
                else:
                    return int(raw)
            except ValueError:
                return raw
    # if not a string, return as is (numbers, bools, etc)
    return raw

def extract_field(row, field_name):
    return str(row[field_name]).strip() if not pd.isna(row[field_name]) else None

def parse_excel_to_transport_profile_builder(df) -> transportProfileBuilder:
    ''' returns a transportProfileBuilder instance based on the DataFrame input '''

    for _, row in df.iterrows():
        if row['ObjectName'] == 'Transport Profile' and row['Type'] == 'main':
            name = str(row['Name']).strip()
            description = str(row['Description']).strip()
            builder = transportProfileBuilder(name=name, description=description)
    logging.getLogger('json_payload').info(f"Transport and Management Profile json payload: {builder.json()}")
    return builder


def parse_excel_to_vpn_builder(df) -> VpnBuilder:
    '''Returns a VpnBuilder instance based on the DataFrame input'''
    df = df[df['Type'] == 'vpn'].copy()
    builders = []
    
    df['Name'] = df['Name'].astype(str)

    for name, group in df.groupby("Name"):
        description = extract_field(group.iloc[0], 'Description')
        builder = VpnBuilder(name=name, description=description)

        # Handle root level fields first
        root_rows = group[group['section'] == 'vpn_root']
        for _, row in root_rows.iterrows():
            field = extract_field(row, 'fieldName')
            if field:
                option_type = extract_field(row, 'optionType') or 'default'
                value = parse_value(row['value'])
                builder.set_path_option("", field, option_type, value)

        # --- Handle list-based objects: ipv4Route ---
        route_rows = group[group['section'].str.contains('ipv4Route', na=False)].copy()
        if not route_rows.empty:
            route_rows['route_index'] = route_rows['section'].str.extract(r'ipv4Route\.(\d+)').fillna('-1')
            
            for _, route_group in route_rows.groupby('route_index'):
                route_fields = {}
                next_hops = []
                
                # Separate nextHop rows from other route fields
                nh_rows = route_group[route_group['section'].str.contains('nextHop', na=False)].copy()
                if not nh_rows.empty:
                    nh_rows['nh_index'] = nh_rows['section'].str.extract(r'nextHop\.(\d+)').fillna('-1')
                    for _, nh_group in nh_rows.groupby('nh_index'):
                        nh_fields = {}
                        for _, row in nh_group.iterrows():
                            field = extract_field(row, 'fieldName')
                            if field:
                                nh_fields[field] = (extract_field(row, 'optionType'), parse_value(row['value']))
                        if all(f in nh_fields for f in ['address', 'distance']):
                            next_hops.append(nh_fields)

                # Process main route fields and prefix fields
                main_route_rows = route_group[~route_group['section'].str.contains('nextHop', na=False)]
                prefix_fields = {}
                for _, row in main_route_rows.iterrows():
                    field = extract_field(row, 'fieldName')
                    section = extract_field(row, 'section')
                    if not field: continue
                    
                    if 'prefix' in section:
                        prefix_fields[field] = (extract_field(row, 'optionType'), parse_value(row['value']))
                    elif not section.endswith('.nextHop.0'):
                        route_fields[field] = (extract_field(row, 'optionType'), parse_value(row['value']))

                # Add the route if we have the necessary fields
                if prefix_fields and 'distance' in route_fields and 'gateway' in route_fields:
                    builder.add_ipv4_route(
                        next_hops=next_hops,
                        distance=route_fields['distance'],
                        prefix=prefix_fields,
                        gateway=route_fields['gateway']
                    )

        # --- Handle all other fields using set_path_option ---
        simple_field_rows = group[~group['section'].str.contains('ipv4Route|vpn_root', na=False)]
        for _, row in simple_field_rows.iterrows():
            section = extract_field(row, 'section')
            field = extract_field(row, 'fieldName')
            option_type = extract_field(row, 'optionType')
            value = parse_value(row['value'])

            if not field or not option_type:
                continue
            
            # Skip list-based fields that require a dedicated 'add' method
            if field in {"newHostMapping", "ipv6Route", "service"}:
                logging.warning(f"Skipping list-based field '{field}'. It requires a dedicated 'add' method.")
                continue

            try:
                # Use 'vpn_root' for root-level options
                path = section if section else "vpn_root"
                builder.set_path_option(path, field, option_type, value)
            except (KeyError, TypeError, NotImplementedError) as e:
                logging.warning(f"Skipping row due to error: {e}. Profile: {name}, Row: {row.to_dict()}")
        
        builders.append(builder)

    for builder in builders:
        logging.getLogger('json_payload').info(f"VPN json payload for '{builder.name}': {builder.json(indent=2)}")

    return builders


def parse_excel_to_interface_builders(df) -> list:
    """
    Parse Excel DataFrame and return a list of InterfaceBuilder objects,
    one per unique 'Name' in the Excel, only for Type == 'interface'.
    """
    df = df[df['Type'] == 'interface'].copy()  # Only process interface rows
    builders = []
    
    # Handle potential float values in 'Name' column
    df['Name'] = df['Name'].astype(str)

    for name, group in df.groupby("Name"):
        description = extract_field(group.iloc[0], 'Description')
        builder = InterfaceBuilder(name=name, description=description)

        # --- Handle list-based objects first ---

        # Collect encapsulation fields
        encap_rows = group[group['section'].str.startswith('encapsulation', na=False)].copy()
        if not encap_rows.empty:
            # Use regex to extract an index from the section string, e.g., "encapsulation.0" -> "0"
            encap_rows['encap_index'] = encap_rows['section'].str.extract(r'encapsulation\.(\d+)').fillna('-1')
            
            for _, encap_group in encap_rows.groupby('encap_index'):
                encap_fields = {}
                for _, row in encap_group.iterrows():
                    field = extract_field(row, 'fieldName')
                    option_type = extract_field(row, 'optionType')
                    value = parse_value(row['value'])
                    if field:
                        encap_fields[field] = (option_type, value)
                
                # Check if all required fields for an encapsulation entry are present
                if all(f in encap_fields for f in ['preference', 'weight', 'encap']):
                    builder.add_encapsulation(
                        preference=encap_fields['preference'],
                        weight=encap_fields['weight'],
                        encap=encap_fields['encap']
                    )

        # --- Handle all other fields using set_path_option ---
        
        # Filter out the rows that have already been processed
        simple_field_rows = group[~group['section'].str.startswith('encapsulation', na=False)]

        for _, row in simple_field_rows.iterrows():
            section = extract_field(row, 'section')
            field = extract_field(row, 'fieldName')
            option_type = extract_field(row, 'optionType')
            value = parse_value(row['value'])

            # Skip if essential data is missing
            if not field or not option_type:
                continue
            
            # Skip list-based fields that require a dedicated 'add' method for now
            if field in {"arp"}: # 'encapsulation' is already filtered out
                logging.warning(f"Skipping list-based field '{field}'. It requires a dedicated 'add' method in the builder.")
                continue

            try:
                builder.set_path_option(section, field, option_type, value)
            except (KeyError, TypeError, NotImplementedError) as e:
                logging.warning(f"Skipping row due to error: {e}. Profile: {name}, Row: {row.to_dict()}")

        builders.append(builder)

    for builder in builders:
        logging.getLogger('json_payload').info(f"Interfaces json payload for '{builder.name}': {builder.json(indent=2)}")

    return builders


def parse_excel_to_bgp_builder(df) -> "BGPBuilder":
    """
    Parse Excel DataFrame and return a BGPBuilder object.
    Only processes rows where Type == 'bgp'.
    """
    df = df[df['Type'] == 'bgp'].copy()
    if df.empty:
        logging.warning("No BGP configuration found in the Excel sheet.")
        return None

    # Initialize builder with info from the first row
    name = str(df.iloc[0]['Name']).strip()
    description = extract_field(df.iloc[0], 'Description')
    builder = BGPBuilder(name=name, description=description)

    # --- Data structures to map Excel indices to actual builder indices ---
    neighbor_map = {}  # excel_neighbor_idx -> actual_neighbor_idx
    redistribute_map = {}  # excel_redistribute_idx -> actual_redistribute_idx
    # (excel_neighbor_idx, excel_af_idx) -> actual_af_idx
    neighbor_af_map = {}

    # --- Sort rows to process parents before children ---
    # e.g., 'neighbor.0' comes before 'neighbor.0.addressFamily.0'
    df['section_len'] = df['section'].str.count('\\.')
    df_sorted = df.sort_values(by='section_len').reset_index(drop=True)

    for _, row in df_sorted.iterrows():
        section = extract_field(row, 'section')
        field = extract_field(row, 'fieldName')
        option_type = extract_field(row, 'optionType')
        value = parse_value(row['value'])

        if not all([section, field, option_type]):
            continue

        parts = section.split('.')
        path = ""

        try:
            if section == 'bgp_root':
                path = ""
            elif section == 'addressFamily':
                path = "addressFamily"
            elif parts[0] == 'addressFamily':
                # This is a redistribute protocol, e.g., 'addressFamily.0'
                excel_idx = int(parts[1])
                if excel_idx not in redistribute_map:
                    actual_idx = builder.add_redistribute_protocol()
                    redistribute_map[excel_idx] = actual_idx
                
                actual_idx = redistribute_map[excel_idx]
                path = f"addressFamily.redistribute[{actual_idx}]"
            
            elif parts[0] == 'neighbor':
                excel_neighbor_idx = int(parts[1])
                if excel_neighbor_idx not in neighbor_map:
                    actual_neighbor_idx = builder.add_neighbor()
                    neighbor_map[excel_neighbor_idx] = actual_neighbor_idx
                
                actual_neighbor_idx = neighbor_map[excel_neighbor_idx]
                
                # Base path for the neighbor
                path_parts = [f"neighbor[{actual_neighbor_idx}]"]

                if len(parts) > 2 and parts[2] == 'addressFamily':
                    excel_af_idx = int(parts[3])
                    map_key = (excel_neighbor_idx, excel_af_idx)

                    if map_key not in neighbor_af_map:
                        actual_af_idx = builder.add_address_family_to_neighbor(actual_neighbor_idx)
                        neighbor_af_map[map_key] = actual_af_idx
                    
                    actual_af_idx = neighbor_af_map[map_key]
                    path_parts.append(f"addressFamily[{actual_af_idx}]")

                    # Handle maxPrefixConfig nested inside addressFamily
                    if len(parts) > 4 and parts[4] == 'maxPrefixConfig':
                        path_parts.append('maxPrefixConfig')
                
                path = ".".join(path_parts)
            
            else:
                logging.warning(f"Unsupported section format: '{section}'. Skipping row.")
                continue

            builder.set_path_option(path, field, option_type, value)

        except (KeyError, TypeError, IndexError, ValueError) as e:
            logging.error(f"Error processing row for section '{section}': {e}. Row data: {row.to_dict()}")

    logging.getLogger('json_payload').info(f"BGP json payload for '{builder.name}': {builder.json(indent=2)}")
    return builder