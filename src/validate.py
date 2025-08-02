import os
import yaml
import json
import argparse
import logging
from jsonschema import validate, ValidationError, SchemaError

# Configure logging for clear output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants and Configuration ---
# Set the base directory where schemas are stored
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_ROOT_DIR = os.path.join(BASE_DIR, 'schemas')

def _load_schema(schema_version: str, schema_name: str) -> dict:
    """
    Loads a JSON schema from the file system for a specific version.

    Args:
        schema_version: The version string (e.g., 'v0.0.0').
        schema_name: The name of the schema file (e.g., 'project.json').

    Returns:
        A dictionary representing the loaded JSON schema.

    Raises:
        FileNotFoundError: If the schema file does not exist.
        json.JSONDecodeError: If the schema file is not valid JSON.
    """
    schema_path = os.path.join(SCHEMA_ROOT_DIR, schema_version, schema_name)
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    logging.info(f"Loading schema from: {schema_path}")
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    return schema

def validate_file_schema(file_path: str, schema_version: str) -> bool:
    """
    Validates a YAML file against its corresponding schema for a given version.

    This function determines the schema name from the file name, loads the
    appropriate schema, and then attempts to validate the file's contents.

    Args:
        file_path: The full path to the YAML file to validate.
        schema_version: The version of the schema to check against (e.g., 'v0.0.0').

    Returns:
        True if the file is valid, False otherwise.
    """
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False

    # Determine schema name from file name (e.g., 'project.yml' -> 'project.json')
    schema_name = os.path.basename(file_path).replace('.yml', '.json')

    try:
        # Load the schema and the data to be validated
        schema = _load_schema(schema_version, schema_name)
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        # Perform the validation
        validate(instance=data, schema=schema)
        logging.info(f"File '{file_path}' is VALID for schema version '{schema_version}'.")
        return True

    except FileNotFoundError as e:
        logging.error(f"Validation failed: {e}")
        return False
    except json.JSONDecodeError:
        logging.error(f"Validation failed: The schema file for '{schema_version}' is not valid JSON.")
        return False
    except yaml.YAMLError as e:
        logging.error(f"Validation failed: The file '{file_path}' is not valid YAML. Error: {e}")
        return False
    except ValidationError as e:
        logging.error(f"File '{file_path}' FAILED validation against schema version '{schema_version}'.")
        logging.error(f"Validation Error: {e.message}")
        return False
    except SchemaError as e:
        logging.error(f"Validation failed: The schema itself is invalid. Error: {e.message}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during validation: {e}")
        return False

def find_schema_version(file_path: str) -> str | None:
    """
    Finds the correct schema version for a given YAML file by attempting
    validation from the latest version down to the oldest.

    Args:
        file_path: The full path to the YAML file to validate.

    Returns:
        The version string of the first successful schema match, or None if no
        matching schema is found.
    """
    schema_versions = sorted(os.listdir(SCHEMA_ROOT_DIR), reverse=True)
    if not schema_versions:
        logging.error(f"No schema versions found in '{SCHEMA_ROOT_DIR}'.")
        return None

    logging.info(f"Attempting to find schema version for '{file_path}'...")
    for version in schema_versions:
        # Use a temporary logger to avoid cluttering output for each failed attempt
        try:
            temp_logger = logging.getLogger('temp')
            temp_logger.setLevel(logging.WARNING)
            with temp_logger.disabled(level=logging.INFO):
                if validate_file_schema(file_path, version):
                    logging.info(f"Successfully identified schema version: {version}")
                    return version
        except Exception:
            # Continue to the next version if an error occurs
            continue

    logging.warning(f"Could not find a valid schema version for '{file_path}'.")
    return None

def main():
    """Command-line interface for the validator script."""
    parser = argparse.ArgumentParser(
        description="Validate a YAML file against a specific schema version, or find its version.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'file_path',
        type=str,
        help="The path to the YAML file to validate (e.g., .prsm/project.yml)."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--version',
        type=str,
        help="The schema version to validate against (e.g., 'v0.0.0')."
    )
    group.add_argument(
        '--find-version',
        action='store_true',
        help="Finds the correct schema version for the file automatically."
    )

    args = parser.parse_args()

    if args.find_version:
        version = find_schema_version(args.file_path)
        if version:
            print(f"The schema version for '{args.file_path}' is: {version}")
    elif args.version:
        validate_file_schema(args.file_path, args.version)

if __name__ == "__main__":
    main()
