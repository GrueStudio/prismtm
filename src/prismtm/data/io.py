import tempfile, yaml, json, os
from typing import Union, Dict, Any, Type
from pathlib import Path
from prismtm.recovery import FileOperationError, FatalError
from prismtm.logs import get_logger
from prismtm.models import BaseYAMLModel

log = get_logger("io")

DATA_YAML = 0
DATA_JSON = 1

def _cleanup(temp_file, temp_path):
    # Always clean up temporary file first
    temp_file_path = None

    # Determine which temp file path to clean up
    if temp_path is not None:
        temp_file_path = temp_path
    elif (temp_file is not None and
          hasattr(temp_file, 'name') and
          os.path.exists(temp_file.name)):
        temp_file_path = temp_file.name

    # Clean up the temporary file if it exists and we didn't succeed
    if temp_file_path is not None and os.path.exists(temp_file_path) and not success:
        try:
            os.unlink(temp_file_path)
            log.debug(f"Cleaned up temporary file: {temp_file_path}")
        except OSError as cleanup_error:
            # Don't raise from finally block, just log
            log.warning(f"Could not clean up temp file {temp_file_path}: {cleanup_error}")

def _create_dirs(file_path : Path):
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        error_msg = f"Cannot create directory {file_path.parent}: {e}"
        log.error(error_msg)
        raise FileOperationError(error_msg) from e

def atomic_write(data_type : int, file_path : Union[Path, str], data : Dict[str, Any], create_dirs : bool = False):
    """
    Serialize and save data to a YAML file using atomic updates.
    """
    file_path = Path(file_path)
    temp_file = None
    temp_path = None

    try:
        # Create directories if requested and needed
        if create_dirs:
            _create_dirs(file_path)

        # Create temporary file in the same directory as target for atomicity
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=file_path.parent, prefix=f".{file_path.name}.", suffix='.tmp', delete=False) as temp_file:
            # Attempt serialization - this is where YAMLError occurs if data is bad
            if data_type == DATA_YAML:
                yaml.safe_dump(data, temp_file, default_flow_style=False, sort_keys=False, indent=2, allow_unicode=True)
            elif data_type == DATA_JSON:
                json.dump(data, temp_file, indent=2, ensure_ascii=False)
            else:
                raise FatalError("Unsupported Data Format")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = temp_file.name

        # Atomic replace - this either completely succeeds or completely fails
        os.replace(temp_path, file_path)
        log.debug(f"Successfully saved YAML file: {file_path}")
        return True

    except (yaml.YAMLError, TypeError) as e:
        _cleanup(temp_file, temp_path)
        # FATAL ERROR: Data cannot be serialized
        error_msg = (f"Data serialization failed for {file_path}. "
                    f"In-memory data may be corrupt or contain non-serializable types: {e}")
        log.critical(error_msg)
        raise FatalError(error_msg) from e

    except (IOError, OSError, PermissionError) as e:
        _cleanup(temp_file, temp_path)
        # RECOVERABLE ERROR: I/O issues
        error_msg = f"I/O error saving YAML file {file_path}: {e}"
        log.error(error_msg)
        raise FileOperationError(error_msg) from e

    except Exception as e:
        _cleanup(temp_file, temp_path)
        # UNEXPECTED FATAL ERROR
        error_msg = f"Unexpected error saving YAML file {file_path}: {e}"
        log.critical(error_msg)
        raise FatalError(error_msg) from e
    return False

def load_model(model_type : Type[BaseYAMLModel], file_path : Union[Path, str]) -> Union[None, BaseYAMLModel]:
    """
    Load and parse a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed data as dict, or None if file doesn't exist or parsing fails
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return model_type.from_yaml(f.read())

    except json.JSONDecodeError as e:
        # YAML syntax errors are typically fatal (corrupted file)
        raise FatalError(f"JSON syntax error in {file_path}: {e}") from e
    except (IOError, OSError, PermissionError) as e:
        # I/O errors are recoverable
        raise FileOperationError(f"Failed to read file {file_path}: {e}") from e
    except Exception as e:
        # Unexpected errors
        raise FatalError(f"Unexpected error loading {file_path}: {e}") from e

def load_json_file(file_path : Union[Path, str]) -> Union[None, Dict]:
    """
    Load and parse a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed data as dict, or None if file doesn't exist or parsing fails
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}

            # Basic sanity check for data corruption
            if not isinstance(data, (dict, type(None))):
                raise FatalError(f"File {file_path} contains invalid data structure")

            return data

    except json.JSONDecodeError as e:
        # YAML syntax errors are typically fatal (corrupted file)
        raise FatalError(f"JSON syntax error in {file_path}: {e}") from e
    except (IOError, OSError, PermissionError) as e:
        # I/O errors are recoverable
        raise FileOperationError(f"Failed to read file {file_path}: {e}") from e
    except Exception as e:
        # Unexpected errors
        raise FatalError(f"Unexpected error loading {file_path}: {e}") from e
