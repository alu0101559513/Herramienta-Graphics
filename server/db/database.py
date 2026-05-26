from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from server.core.config import settings
from server.models.analysis import Analysis
from server.models.user import User

mongo_client: AsyncIOMotorClient | None = None
mongo_database = None
gridfs_bucket: AsyncIOMotorGridFSBucket | None = None


async def init_db() -> None:
    """
    Description:
        Initialize MongoDB, GridFS and Beanie ODM resources.

        This function creates the global Motor client, selects the configured
        database, initializes the GridFS bucket, and registers the Beanie document
        models used by the application.

    Args:
        None.

    Returns:
        None:
            Initializes module-level database resources.
    """

    global mongo_client, mongo_database, gridfs_bucket

    mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
    mongo_database = mongo_client[settings.DB_NAME]
    gridfs_bucket = AsyncIOMotorGridFSBucket(mongo_database)

    await init_beanie(
        database=mongo_database,
        document_models=[User, Analysis],
    )


def get_database():
    """
    Description:
        Return the initialized MongoDB database handle.

    Args:
        None.

    Returns:
        Any:
            Motor database instance.

    Raises:
        RuntimeError:
            Raised when the database has not been initialized yet.
    """

    if mongo_database is None:
        raise RuntimeError("Database is not initialized")

    return mongo_database


def get_gridfs() -> AsyncIOMotorGridFSBucket:
    """
    Description:
        Return the initialized GridFS bucket handle.

    Args:
        None.

    Returns:
        AsyncIOMotorGridFSBucket:
            GridFS bucket instance used to store and retrieve files.

    Raises:
        RuntimeError:
            Raised when GridFS has not been initialized yet.
    """

    if gridfs_bucket is None:
        raise RuntimeError("GridFS is not initialized")

    return gridfs_bucket
