import abc
from typing import Dict

# This is a sample type for the data structure we're migrating.
# Replace with a more specific type if your schema is known.
MigrationData = Dict

class Migration(abc.ABC):
    """
    An abstract base class for all migration scripts.

    Each concrete migration class must implement the upgrade() and downgrade()
    methods to handle schema changes for a specific version jump.
    """
    # The 'version' attribute should be a string representing the target version
    # of the schema this migration script is upgrading to (e.g., 'v0.0.1').
    VERSION = None

    @abc.abstractmethod
    def upgrade(self, data: MigrationData) -> MigrationData:
        """
        Applies schema changes to the data to upgrade it to the new version.

        Args:
            data: The dictionary representing the data to be migrated.

        Returns:
            The migrated data dictionary.
        """
        pass

    @abc.abstractmethod
    def downgrade(self, data: MigrationData) -> MigrationData:
        """
        Reverts schema changes to downgrade the data to the previous version.

        Args:
            data: The dictionary representing the data to be reverted.

        Returns:
            The downgraded data dictionary.
        """
        pass
