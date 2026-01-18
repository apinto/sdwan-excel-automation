

import pandas as pd
import logging
from modules.cli.profile import CliProfileBuilder
from modules.cli.cli import CliBuilder


def parse_excel_to_cli_profiles_builder(df: pd.DataFrame) -> list[CliProfileBuilder]:
    """
    Returns a list of CliProfileBuilder instances based on the DataFrame input
    """
    builders = []
    for _, row in df.iterrows():
        if row['ObjectName'] == 'CLI-Profile':
            name = str(row['Name']).strip()
            description = str(row.get('Description', '')).strip()
            builder = CliProfileBuilder(name=name, description=description)
            builders.append(builder)
            logging.getLogger('json_payload').info(f"CLI Main Profile json payload for {name}: {builder.json()}")
    return builders

def parse_excel_to_cli_builder(df: pd.DataFrame) -> list[CliBuilder]:
    """
    Returns a list of CliBuilder instances based on the DataFrame input
    """
    builders = []
    for _, row in df.iterrows():
        if row['ObjectName'] == 'CLI-Profile':
            name = str(row['Name']).strip()
            config = str(row.get('Config', '')).strip()
            builder = CliBuilder(name=name, config=config)
            builders.append(builder)
            logging.getLogger('json_payload').info(f"CLI Profile json payload for {name}: {builder.json()}")
    return builders
