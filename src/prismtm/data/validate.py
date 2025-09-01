import os
import yaml
import json
from prismtm.logs import get_logger
from pathlib import Path

from prismtm.version import APP_SCHEMA_VERSION
from .io import load_json_file
from jsonschema import validate, ValidationError, SchemaError

PROJECT_DATA_DIR = Path(".prsm")
USER_DATA_DIR = Path.home() / ".local" / "share" / "prismtm" / "data"

NO_PROJECT = "No Project"

PROJECT_SCOPE = 0
USER_SCOPE = 1

# Configure log for clear output
log = get_logger("data.validate")

# --- Constants and Configuration ---
# Set the base directory where schemas are stored
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    schema_path = os.path.join(SCHEMA_ROOT_DIR, f"v{schema_version}", schema_name)
    log.debug(f"Schema Path: {schema_path}")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    log.info(f"Loading schema from: {schema_path}")
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
        log.error(f"File not found: {file_path}")
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
        log.info(f"File '{file_path}' is VALID for schema version '{schema_version}'.")
        return True

    except FileNotFoundError as e:
        log.error(f"Validation failed: {e}")
        return False
    except json.JSONDecodeError:
        log.error(f"Validation failed: The schema file for '{schema_version}' is not valid JSON.")
        return False
    except yaml.YAMLError as e:
        log.error(f"Validation failed: The file '{file_path}' is not valid YAML. Error: {e}")
        return False
    except ValidationError as e:
        log.error(f"File '{file_path}' FAILED validation against schema version '{schema_version}'.")
        log.error(f"Validation Error: {e.message}")
        return False
    except SchemaError as e:
        log.error(f"Validation failed: The schema itself is invalid. Error: {e.message}")
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred during validation: {e}")
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
        log.error(f"No schema versions found in '{SCHEMA_ROOT_DIR}'.")
        return None

    log.info(f"Attempting to find schema version for '{file_path}'...")
    for version in schema_versions:
        # Use a temporary logger to avoid cluttering output for each failed attempt
        try:
            if validate_file_schema(file_path, version):
                log.info(f"Successfully identified schema version: {version}")
                return version
        except Exception:
            # Continue to the next version if an error occurs
            continue

    log.warning(f"Could not find a valid schema version for '{file_path}'.")
    return None

def find_schema_versions() -> tuple:
    project = _get_meta_version(PROJECT_DATA_DIR / "meta.json")
    if project == None:
        project = _validate_schemas_backwards(PROJECT_SCOPE)
    user = _get_meta_version(USER_DATA_DIR / "meta.json")
    if user == None:
        user = _validate_schemas_backwards(USER_SCOPE)
    return (project, user)

def _get_meta_version(meta_file : Path) -> str | None:
    if not os.path.exists(meta_file):
        return None
    meta_data = load_json_file(meta_file)

    if meta_data != None:
        return meta_data["schema_version"]

    return None

def _validate_schemas_backwards(scope: int) -> str:
    """
    Find the most recent schema version that successfully validates all files
    in the given scope by checking backwards from latest to oldest versions.

    Args:
        scope: Either PROJECT_SCOPE or USER_SCOPE

    Returns:
        The most recent schema version string that validates successfully,
        or "0.0.0" if no validation succeeds
    """
    # Determine the data directory and scope prefix based on scope
    if scope == PROJECT_SCOPE:
        data_dir = PROJECT_DATA_DIR
        scope_prefix = "project"
    elif scope == USER_SCOPE:
        data_dir = USER_DATA_DIR
        scope_prefix = "user"
    else:
        log.error(f"Invalid scope: {scope}")
        return "0.0.0"

    if not data_dir.exists():
        log.warning(f"Data directory does not exist: {data_dir}")
        return "0.0.0"

    # Get all schema versions sorted from latest to oldest
    schema_versions = sorted(os.listdir(SCHEMA_ROOT_DIR), reverse=True)
    if not schema_versions:
        log.error(f"No schema versions found in '{SCHEMA_ROOT_DIR}'.")
        return "0.0.0"

    # Find all YAML files in the data directory
    yaml_files = list(data_dir.glob("*.yml"))
    if not yaml_files:
        log.warning(f"No YAML files found in {data_dir}")
        return "0.0.0"

    log.info(f"Searching for compatible schema version for scope {scope} with {len(yaml_files)} files...")

    # Try each schema version from latest to oldest
    for version in schema_versions:
        all_valid = True

        # Validate each file against this schema version
        for yaml_file in yaml_files:
            # Convert filename to schema name: filename.yml -> scope_filename.schema.json
            base_name = yaml_file.stem  # gets 'bugs' from 'bugs.yml'
            schema_name = f"{scope_prefix}_{base_name}.schema.json"

            try:
                schema = _load_schema(version, schema_name)
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                # Perform validation
                validate(instance=data, schema=schema)

            except FileNotFoundError:
                # Schema file doesn't exist for this version, try next version
                all_valid = False
                break
            except (json.JSONDecodeError, yaml.YAMLError, ValidationError, SchemaError):
                # Validation failed for this version, try next version
                all_valid = False
                break
            except Exception as e:
                log.debug(f"Unexpected error with version {version}: {e}")
                all_valid = False
                break

        if all_valid:
            log.info(f"Found compatible schema version {version} for scope {scope}")
            return version

    log.warning(f"No compatible schema version found for scope {'"user"' if scope == 1 else '"project"'}")
    return "0.0.0"

def validate_scope_schema(scope: int, version : str = APP_SCHEMA_VERSION) -> bool:
    """
    Validate all files in the given scope against their current schema versions.

    Args:
        scope: Either PROJECT_SCOPE or USER_SCOPE

    Returns:
        True if all files are valid, False otherwise
    """
    # Determine the data directory, scope prefix, and meta file based on scope
    if scope == PROJECT_SCOPE:
        data_dir = PROJECT_DATA_DIR
        scope_prefix = "project"
    elif scope == USER_SCOPE:
        data_dir = USER_DATA_DIR
        scope_prefix = "user"
    else:
        log.error(f"Invalid scope: {scope}")
        return False

    if not data_dir.exists():
        log.warning(f"Data directory does not exist: {data_dir}")
        return False

    # Find all YAML files in the data directory
    yaml_files = list(data_dir.glob("*.yml"))
    if not yaml_files:
        log.warning(f"No YAML files found in {data_dir}")
        return True  # Empty directory is considered valid

    log.info(f"Validating {len(yaml_files)} files in scope {scope} against schema version {version}...")

    # Validate each file against the current schema version
    all_valid = True
    for yaml_file in yaml_files:
        # Convert filename to schema name: filename.yml -> scope_filename.schema.json
        base_name = yaml_file.stem  # gets 'bugs' from 'bugs.yml'
        schema_name = f"{scope_prefix}_{base_name}.schema.json"

        try:
            schema = _load_schema(version, schema_name)
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)

            # Perform validation
            validate(instance=data, schema=schema)
            log.debug(f"✓ {yaml_file.name} is valid")

        except FileNotFoundError:
            log.error(f"Schema file '{schema_name}' not found for version {version}")
            all_valid = False
        except json.JSONDecodeError:
            log.error(f"Schema file '{schema_name}' is not valid JSON")
            all_valid = False
        except yaml.YAMLError as e:
            log.error(f"File {yaml_file.name} is not valid YAML: {e}")
            all_valid = False
        except ValidationError as e:
            log.error(f"File {yaml_file.name} FAILED validation: {e.message}")
            all_valid = False
        except SchemaError as e:
            log.error(f"Schema '{schema_name}' is invalid: {e.message}")
            all_valid = False
        except Exception as e:
            log.error(f"Unexpected error validating {yaml_file.name}: {e}")
            all_valid = False

    if all_valid:
        log.info(f"All files in scope {scope} are VALID against schema version {version}")
    else:
        log.error(f"Some files in scope {scope} FAILED validation against schema version {version}")

    return all_valid
