# SD-WAN vManager Configuration Automation

A Python-based automation tool for configuring Cisco SD-WAN vManager using Excel spreadsheets as the configuration source. This tool reads configuration parameters from Excel files and creates feature profiles, parcels, and configuration groups via the vManager REST API.

## Overview

This project provides an SDK-like framework to automate the creation of SD-WAN configuration objects including:
- **System Profiles** (AAA, BFD, OMP, NTP, Logging, SNMP, Security, etc.)
- **Transport Profiles** (VPNs, Interfaces, BGP)
- **Service Profiles** (VPNs, Interfaces)
- **CLI Profiles** (Custom CLI configurations)
- **Configuration Groups** (Profile associations and device configurations)

The tool uses Pydantic models for JSON payload generation and validation, ensuring type safety and proper data structure for vManager API calls.

## Features

- **Excel-Driven Configuration**: Define all configuration parameters in a structured Excel file (`input.xlsx`)
- **Modular Architecture**: Organized folder structure that mirrors vManager GUI and API organization
- **Type Safety**: Pydantic models ensure data validation and proper JSON structure
- **Hierarchical Object Creation**: Automatically handles dependencies (profiles → VPNs → interfaces)
- **Audit Trail**: Tracks all created objects with IDs in `objects_created.xlsx`
- **Execution Summary**: Provides detailed summary of objects created during each run
- **Flexible Execution**: Run all configurations or select specific feature types
- **Comprehensive Logging**: Dual logging system (console + detailed file logs)

## Project Structure

```
├── input.xlsx                    # Excel file with configuration data
├── excel2sdwan.py               # Main orchestrator script
├── objects_created.xlsx         # Audit trail of created objects
├── vmanager_conf.log            # Detailed execution logs
├── cleanup-excel2sdwan.py       # Utility to clean up created objects
├── LICENSE                      # MIT License
└── modules/
    ├── system/                  # System feature profiles
    │   ├── profile.py
    │   ├── aaa.py
    │   ├── bfd.py
    │   ├── omp.py
    │   ├── ntp.py
    │   ├── logg.py
    │   ├── snmp.py
    │   ├── security.py
    │   ├── banner.py
    │   ├── basic.py
    │   ├── globall.py
    │   └── parsers.py
    ├── transport/               # Transport feature profiles
    │   ├── profile.py
    │   ├── vpn.py
    │   ├── interface.py
    │   ├── bgp.py
    │   └── parsers.py
    ├── service/                 # Service feature profiles
    │   ├── profile.py
    │   ├── vpn.py
    │   ├── interface.py
    │   └── parsers.py
    ├── cli/                     # CLI profiles
    │   ├── profile.py
    │   ├── cli.py
    │   └── parsers.py
    └── conf_groups/             # Configuration groups
        ├── cg_model.py
        ├── cgroup.py
        └── parsers.py
```

## Prerequisites

- Python 3.8 or higher
- Cisco SD-WAN vManager (tested on version 20.x)
- Network access to vManager
- Valid vManager credentials with appropriate permissions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/apinto/sdwan-excel-automation.git
cd sdwan-excel-automation
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install catalystwan pandas openpyxl
```

4. Update vManager credentials in `excel2sdwan.py`:
```python
url      = "https://your-vmanager-ip"
username = "your-username"
password = "your-password"
```

## Usage

### Basic Usage

Run all configuration types in order (system → transport → service → cli → config-groups):
```bash
python excel2sdwan.py
```

### Selective Execution

Run specific feature types:
```bash
# Run only system profiles
python excel2sdwan.py --feature-type system

# Run multiple specific types
python excel2sdwan.py --feature-type system,transport,service

# Run only configuration groups (requires profiles to exist)
python excel2sdwan.py --feature-type config-groups
```

### Get Help

```bash
python excel2sdwan.py --help
```

## Excel File Structure

The `input.xlsx` file should contain worksheets for each configuration type:
- **system**: System profile and parcels configuration
- **transport**: Transport profile and parcels configuration
- **service**: Service profile and parcels configuration
- **cli**: CLI profile and configurations
- **ConfGroups**: Configuration groups that reference other profiles

Each worksheet follows a specific column structure with fields like:
- `ObjectName`: Name of the configuration object
- `Type`: Object type (profile, parcel, etc.)
- `section`: Configuration section
- `fieldName`: API field name
- `optionType`: Configuration option type (default, global, variable)
- `value`: Configuration value

## How It Works

1. **Excel Parsing**: Reads configuration data from `input.xlsx` worksheets
2. **Pydantic Model Building**: Constructs type-safe Pydantic models with proper validation
3. **JSON Payload Generation**: Converts Pydantic models to JSON payloads for vManager API
4. **API Calls**: Posts configurations to vManager REST API in the correct order
5. **Object Tracking**: Saves created object IDs to `objects_created.xlsx`
6. **Dependency Resolution**: For config groups, resolves profile names to IDs from the audit file

## Output Files

- **objects_created.xlsx**: Audit trail with details of all created objects
  - Run ID and timestamp
  - Object type and name
  - API URL used
  - Object ID returned by vManager
  
- **vmanager_conf.log**: Detailed execution logs
  - Console logs (INFO level)
  - Detailed API request/response (DEBUG level)
  - JSON payloads and responses

## Design Principles

1. **Self-Contained Modules**: Each module (system, transport, service) is independent
2. **Builder Pattern**: Step-by-step construction of configuration objects
3. **Type Safety**: Pydantic ensures proper data types and structure
4. **Default Values**: Modules use default_factory for unspecified fields
5. **Code Consistency**: Uniform coding style across all modules

## Cleanup

The cleanup script provides a safe way to remove objects created by `excel2sdwan.py` from vManager.

### How It Works

The `cleanup-excel2sdwan.py` script:

1. **Reads the Audit Trail**: Loads `objects_created.xlsx` which contains all objects created during previous runs
2. **Tracks by Run ID**: Each execution of `excel2sdwan.py` generates a unique Run ID (timestamp-based)
3. **Reverse Order Deletion**: Processes objects in reverse order (bottom-to-top) to respect dependencies
4. **API-Based Removal**: Makes DELETE requests to vManager REST API for each object
5. **Updates Audit File**: Removes successfully deleted objects from `objects_created.xlsx`

### Object Tracking

Every time `excel2sdwan.py` creates an object, it logs the following information to `objects_created.xlsx`:

| Column | Description |
|--------|-------------|
| **Run ID** | Unique identifier for each execution (epoch timestamp) |
| **Timestamp** | Human-readable date/time of creation |
| **Object Type** | Category (System, Transport, Service, CLI, ConfigGroup) |
| **Name** | Hierarchical name (e.g., `profile.vpn.interface`) |
| **Object Name** | Full descriptive name of the object |
| **URL** | API endpoint used to create the object |
| **ID** | Unique UUID returned by vManager |

This tracking enables:
- Selective deletion by Run ID
- Complete rollback of specific execution runs
- Audit trail for compliance and troubleshooting
- Safe cleanup without affecting manually created objects

### Usage Examples

```bash
# Delete most recent run (default)
python cleanup-excel2sdwan.py

# List all available runs
python cleanup-excel2sdwan.py --list-runs

# Delete a specific run by ID
python cleanup-excel2sdwan.py --run-id 1737241234

# Delete all runs (all tracked objects)
python cleanup-excel2sdwan.py --all-runs

# Dry run - preview what would be deleted
python cleanup-excel2sdwan.py --dry-run

# Remove from Excel only (no API calls)
python cleanup-excel2sdwan.py --run-id 1737241234 --remove-from-excel-only
```

### Important Notes

- Objects are deleted in **reverse order** to handle dependencies correctly
- Successfully deleted objects are **automatically removed** from `objects_created.xlsx`
- Failed deletions remain in the audit file for retry
- All cleanup operations are logged to `vmanager_cleanup.log`

## Contributing

Contributions are welcome! Whether you want to:
- Add support for new feature profiles or parcels
- Improve error handling and validation
- Enhance documentation
- Fix bugs or optimize code
- Add new features

Please feel free to:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Disclaimer

**IMPORTANT**: This tool is provided as-is, without any warranties or guarantees. The authors take no responsibility for any issues, damages, or problems that may arise from using this script. Use at your own risk.

- Always test in a lab environment first
- Review generated configurations before applying to production
- Ensure you have proper backups of your vManager configuration
- Verify API permissions and access controls
- This tool makes changes to your SD-WAN infrastructure - use with caution

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Artur Pinto (arturj.pinto@gmail.com)

## Acknowledgments

- Built using [catalystwan](https://github.com/cisco-open/cisco-catalyst-wan-sdk) SDK
- Inspired by the need to automate repetitive vManager configuration tasks
- Thanks to the Cisco SD-WAN community for their support and feedback
