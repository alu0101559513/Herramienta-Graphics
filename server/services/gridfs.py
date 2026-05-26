from bson import ObjectId
from server.db.database import get_gridfs


async def save_file(filename: str, data: bytes):
    """
    Description:
        Store binary content in GridFS.

    Args:
        filename (str): Logical filename to store.
        data (bytes): File content bytes.

    Returns:
        str: Stored GridFS file ID as string.
    """

    bucket = get_gridfs()

    file_id = await bucket.upload_from_stream(filename, data)

    return str(file_id)


async def get_file(file_id: str):
    """
    Description:
        Retrieve binary content from GridFS by file ID.

    Args:
        file_id (str): Stored GridFS file identifier.

    Returns:
        bytes: File content.
    """

    bucket = get_gridfs()

    stream = await bucket.open_download_stream(ObjectId(file_id))

    return await stream.read()


async def delete_file(file_id: str):
    """
    Description:
        Delete a file from GridFS by file ID.

    Args:
        file_id (str): Stored GridFS file identifier.

    Returns:
        None: File is deleted when it exists.
    """

    bucket = get_gridfs()

    await bucket.delete(ObjectId(file_id))
