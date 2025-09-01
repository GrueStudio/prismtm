class PRISMError(Exception):
    """Base exception for all DataCore errors."""
    pass

class RecoverableError(PRISMError):
    """An error that can be recovered from without data loss."""
    pass

class FatalError(PRISMError):
    """An error that requires application termination or major intervention."""
    pass

class CorruptionError(FatalError):
    """Corrupted Data Error - from syntax errors in data formats, to just unknown data"""
    pass

class MigrationError(CorruptionError):
    """Data migration failed - data may be corrupted."""
    pass

class FileOperationError(RecoverableError):
    """File operation failed but can be retried."""
    pass

class MigrationNeededError(RecoverableError):
    """ Data is valid, but may need a migration """
    pass
