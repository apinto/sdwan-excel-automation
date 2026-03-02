#!/usr/bin/env python

# Author: Artur Pinto (arturj.pinto@gmail.com)

import logging
import sys
import pandas as pd
import argparse
from pathlib import Path
from catalystwan.session import create_manager_session
import urllib3

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vmanager_cleanup.log", mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

# vManager connection details
url = "https://your-vmanager-ip"
username = "your-username"
password = "your-password"

def delete_objects_from_excel(excel_file="objects_created.xlsx", run_id=None, dry_run=False, all_runs=False):
    """
    Read the Excel file containing created objects and delete them from vManager
    in reverse order (bottom to top). Successfully deleted objects are removed from the Excel file.
    
    Args:
        excel_file (str): Path to the Excel file with created objects
        run_id (str, optional): The Run ID to filter objects by. If None, uses the most recent run.
        dry_run (bool): If True, only print what would be deleted without making API calls
        all_runs (bool): If True, delete objects from all runs in the Excel file
    
    Returns:
        int: Number of objects successfully deleted
    """
    try:
        # Read the Excel file
        df = pd.read_excel(excel_file)
        
        # Check if the Excel file has the expected columns
        required_columns = ['Object Name', 'URL', 'ID']
        new_format = all(col in df.columns for col in ['Run ID', 'Timestamp'])
        
        if not all(col in df.columns for col in required_columns):
            logging.error(f"Excel file {excel_file} does not have the required columns: {required_columns}")
            return 0
            
        # Filter by Run ID if the new format is used and all_runs is not specified
        if new_format and not all_runs:
            if run_id is None:
                # Find the most recent run (using timestamp or run ID)
                if 'Timestamp' in df.columns:
                    # Convert to datetime if it's not already
                    if not pd.api.types.is_datetime64_any_dtype(df['Timestamp']):
                        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    # Get the latest timestamp
                    latest_ts = df['Timestamp'].max()
                    logging.info(f"No Run ID specified. Using most recent run from {latest_ts}")
                    # Filter to only that timestamp's rows
                    df = df[df['Timestamp'] == latest_ts]
                else:
                    # Use the latest Run ID if timestamp isn't available
                    latest_run_id = str(df['Run ID'].max())
                    logging.info(f"No Run ID specified. Using most recent run ID: {latest_run_id}")
                    # Filter to only that Run ID's rows
                    df = df[df['Run ID'] == latest_run_id]
            else:
                # Filter to only the specified Run ID's rows
                run_id_str = str(run_id)  # Convert to string for comparison
                df = df[df['Run ID'].astype(str) == run_id_str]
                if len(df) == 0:
                    logging.error(f"No objects found with Run ID: {run_id}")
                    return 0
                logging.info(f"Filtered to {len(df)} objects with Run ID: {run_id}")
        elif all_runs:
            logging.info(f"Processing ALL runs with a total of {len(df)} objects")
            # When all_runs is True, we don't filter by run_id and use all rows
        
        # Reverse the order (process from bottom to top)
        df = df.iloc[::-1].reset_index(drop=True)
        
        logging.info(f"Found {len(df)} objects to delete")
        
        if dry_run:
            logging.info("DRY RUN MODE: No objects will be deleted")
            for index, row in df.iterrows():
                object_name = row['Object Name']
                object_id = row['ID']
                
                # Check for exact profile URL matches and use hardcoded paths for those
                original_url = row['URL']
                
                # Remove "-assoc" suffix from ID if it exists
                clean_object_id = object_id
                if object_id and isinstance(object_id, str) and object_id.endswith("-assoc"):
                    clean_object_id = object_id.replace("-assoc", "")
                    logging.debug(f"Removed -assoc suffix from ID: {object_id} -> {clean_object_id}")
                
                # create delete url
                if original_url.endswith('/'):
                    delete_url = f"{original_url}{clean_object_id}"
                else:
                    delete_url = f"{original_url}/{clean_object_id}"
                if object_id != clean_object_id:
                    logging.info(f"Would delete {row['Object Name']} using URL: {delete_url} (removed -assoc suffix from ID)")
                else:
                    logging.info(f"Would delete {row['Object Name']} using URL: {delete_url}")
            logging.info("DRY RUN: No changes were made to the Excel file")
            return 0
        
        # Connect to vManager
        with create_manager_session(url=url, username=username, password=password) as session:
            successful_deletions = 0
            rows_to_drop = []
            
            # Process each object
            for index, row in df.iterrows():
                #object_name = row['Object Name']
                object_name = row['Name']
                object_id = row['ID']
                
                # Check for exact profile URL matches and use hardcoded paths for those
                original_url = row['URL']
                
                # Remove "-assoc" suffix from ID if it exists
                clean_object_id = object_id
                if object_id and isinstance(object_id, str) and object_id.endswith("-assoc"):
                    clean_object_id = object_id.replace("-assoc", "")
                    logging.debug(f"Removed -assoc suffix from ID: {object_id} -> {clean_object_id}")
                
                # create delete url
                if original_url.endswith('/'):
                    delete_url = f"{original_url}{clean_object_id}"
                else:
                    delete_url = f"{original_url}/{clean_object_id}"
                
                if object_id != clean_object_id:
                    logging.info(f"Deleting {object_name} with ID {object_id} (removing -assoc suffix)...")
                else:
                    logging.info(f"Deleting {object_name} with ID {object_id}...")
                
                try:
                    # Make the DELETE request
                    resp = session.delete(delete_url)
                    resp.raise_for_status()
                    
                    # Check response
                    if resp.status_code in [200, 204]:
                        logging.info(f"SUCCESS: Deleted {object_name} | Status: {resp.status_code}")
                        successful_deletions += 1
                        # Mark this row for removal
                        rows_to_drop.append(index)
                    else:
                        logging.warning(f"WARNING: Unexpected status code {resp.status_code} when deleting {object_name}")
                        
                except Exception as e:
                    logging.error(f"ERROR: Failed to delete {object_name} | URL: {delete_url} | Error: {e}")
                    # Continue with next object even if this one failed
            
            # Remove successfully deleted objects from the Excel file
            if successful_deletions > 0:
                # Read the complete original Excel file
                all_df = pd.read_excel(excel_file)
                
                # We can't directly use the indices from the filtered dataframe
                # Instead, identify the specific rows to remove by matching the IDs that were successfully deleted
                successfully_deleted_ids = [df.loc[idx, 'ID'] for idx in rows_to_drop]
                
                # Keep only the rows where the ID is not in the list of successfully deleted IDs
                all_df = all_df[~all_df['ID'].isin(successfully_deleted_ids)]
                
                # Save the updated Excel file
                all_df.to_excel(excel_file, index=False)
                logging.info(f"Updated Excel file: Removed {len(rows_to_drop)} successfully deleted objects")
            
            logging.info(f"Successfully deleted {successful_deletions} out of {len(df)} objects")
            return successful_deletions
            
    except FileNotFoundError:
        logging.error(f"Excel file {excel_file} not found")
        return 0
    except Exception as e:
        logging.error(f"Error deleting objects: {e}")
        return 0


def list_available_runs(excel_file="objects_created.xlsx"):
    """
    List all available runs in the Excel file.
    
    Args:
        excel_file (str): Path to the Excel file with created objects
        
    Returns:
        None
    """
    try:
        df = pd.read_excel(excel_file)
        
        if 'Run ID' not in df.columns or 'Timestamp' not in df.columns:
            logging.error(f"Excel file {excel_file} does not have the required columns for run tracking")
            return
            
        # Group by Run ID and get the count, timestamp, and a list of object types
        basic_agg = df.groupby('Run ID').agg(
            Count=('ID', 'count'),
            Timestamp=('Timestamp', 'first')
        )
        
        # Get a list of unique object types for each Run ID
        object_types_by_run = {}
        for run_id in df['Run ID'].unique():
            run_data = df[df['Run ID'] == run_id]
            if 'Object Type' in run_data.columns:
                # Get unique object types, convert to strings, filter out NaN, preserve original order
                object_types = [str(t) for t in run_data['Object Type'].unique() if pd.notna(t)]
                object_types_by_run[run_id] = ', '.join(object_types)
            else:
                object_types_by_run[run_id] = 'N/A'
        
        # Add the object types to the dataframe
        runs = basic_agg.reset_index()
        runs['Object Types'] = runs['Run ID'].map(object_types_by_run)
        
        # Sort by timestamp descending
        runs = runs.sort_values('Timestamp', ascending=False)
        
        print("\nAvailable Runs:")
        print("-" * 120)
        print(f"{'Run ID':<20} {'Timestamp':<25} {'Object Count':<15} {'Object Types':<60}")
        print("-" * 120)
        
        for _, row in runs.iterrows():
            # Truncate object types if they're too long and add "..." at the end
            obj_types = row['Object Types']
            if len(obj_types) > 57:
                obj_types = obj_types[:54] + "..."
            print(f"{str(row['Run ID']):<20} {str(row['Timestamp']):<25} {row['Count']:<15} {obj_types:<60}")
            
        print("\n")
        
    except FileNotFoundError:
        logging.error(f"Excel file {excel_file} not found")
    except Exception as e:
        logging.error(f"Error listing runs: {e}")


def remove_run_from_excel(excel_file="objects_created.xlsx", run_id=None):
    """
    Remove all rows for a specific Run ID from the Excel file without making API calls.
    
    Args:
        excel_file (str): Path to the Excel file with created objects
        run_id (str): The Run ID to remove from the Excel file
    
    Returns:
        int: Number of rows removed from the Excel file
    """
    try:
        # Check if run_id is provided
        if not run_id:
            logging.error("Run ID must be specified when using --remove-from-excel-only")
            return 0
        
        # Read the Excel file
        df = pd.read_excel(excel_file)
        
        # Check if the Excel file has the Run ID column
        if 'Run ID' not in df.columns:
            logging.error(f"Excel file {excel_file} does not have the 'Run ID' column")
            return 0
            
        # Get the original row count
        original_count = len(df)
        
        # Convert run_id to appropriate type if necessary
        try:
            # Check if Run ID in the dataframe is numeric
            if pd.api.types.is_numeric_dtype(df['Run ID']):
                run_id = int(run_id)
        except ValueError:
            logging.warning(f"Could not convert Run ID {run_id} to integer. Will try as string.")
        
        # Filter the dataframe to keep only rows with a different Run ID
        df_filtered = df[df['Run ID'] != run_id]
        
        # Calculate how many rows were removed
        removed_count = original_count - len(df_filtered)
        
        if removed_count == 0:
            logging.warning(f"No rows found with Run ID: {run_id}")
            return 0
            
        # Save the updated Excel file
        df_filtered.to_excel(excel_file, index=False)
        logging.info(f"Removed {removed_count} rows with Run ID {run_id} from {excel_file}")
        
        return removed_count
        
    except FileNotFoundError:
        logging.error(f"Excel file {excel_file} not found")
        return 0
    except Exception as e:
        logging.error(f"Error removing rows from Excel: {e}")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Delete objects created in vManager')
    parser.add_argument('-f', '--file', type=str, default='objects_created.xlsx',
                        help='Path to the Excel file with created objects (default: objects_created.xlsx)')
    parser.add_argument('-r', '--run-id', type=str,
                        help='Specific Run ID to delete (default: most recent run)')
    parser.add_argument('-a', '--all-runs', action='store_true',
                        help='Delete objects from all runs in the Excel file')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Show what would be deleted without making any changes')
    parser.add_argument('-l', '--list-runs', action='store_true',
                        help='List all available runs in the Excel file')
    parser.add_argument('-x', '--remove-from-excel-only', action='store_true',
                        help='Remove entries from the Excel file without deleting objects from vManager')
    
    args = parser.parse_args()
    
    # If --list-runs is specified, just list the runs and exit
    if args.list_runs:
        list_available_runs(args.file)
        sys.exit(0)
    
    # If --remove-from-excel-only is specified, remove the run from Excel and exit
    if args.remove_from_excel_only:
        if not args.run_id and not args.all_runs:
            logging.error("--run-id or --all-runs is required when using --remove-from-excel-only")
            sys.exit(1)
        
        if args.all_runs:
            logging.info(f"Removing ALL runs from Excel file: {args.file}")
            # Re-create the Excel file as an empty file with the same columns
            try:
                df = pd.read_excel(args.file)
                empty_df = pd.DataFrame(columns=df.columns)
                empty_df.to_excel(args.file, index=False)
                logging.info(f"Successfully removed all runs from {args.file}")
            except Exception as e:
                logging.error(f"Error removing all runs from Excel: {e}")
                sys.exit(1)
        else:
            logging.info(f"Removing run ID {args.run_id} from Excel file: {args.file}")
            remove_run_from_excel(args.file, args.run_id)
        sys.exit(0)
    
    # Check that run-id and all-runs are not both specified
    if args.run_id and args.all_runs:
        logging.error("Cannot specify both --run-id and --all-runs")
        sys.exit(1)
    
    logging.info(f"Starting cleanup process using file: {args.file}")
    delete_objects_from_excel(args.file, args.run_id, args.dry_run, args.all_runs)
