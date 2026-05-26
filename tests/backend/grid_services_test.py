import pytest
from bson import ObjectId

import server.services.gridfs as gridfs_service


class FakeStream:
    async def read(self):
        return b"file-content"


class FakeBucket:
    def __init__(self):
        self.uploads = []
        self.downloaded_id = None
        self.deleted_id = None

    async def upload_from_stream(self, filename, data):
        self.uploads.append((filename, data))
        return ObjectId("000000000000000000000001")

    async def open_download_stream(self, file_id):
        self.downloaded_id = file_id
        return FakeStream()

    async def delete(self, file_id):
        self.deleted_id = file_id


@pytest.mark.asyncio
async def test_save_file(monkeypatch):
    bucket = FakeBucket()
    monkeypatch.setattr(gridfs_service, "get_gridfs", lambda: bucket)

    result = await gridfs_service.save_file("a.txt", b"hello")

    assert result == "000000000000000000000001"
    assert bucket.uploads == [("a.txt", b"hello")]


@pytest.mark.asyncio
async def test_get_file(monkeypatch):
    bucket = FakeBucket()
    monkeypatch.setattr(gridfs_service, "get_gridfs", lambda: bucket)

    result = await gridfs_service.get_file("000000000000000000000002")

    assert result == b"file-content"
    assert bucket.downloaded_id == ObjectId("000000000000000000000002")


@pytest.mark.asyncio
async def test_delete_file(monkeypatch):
    bucket = FakeBucket()
    monkeypatch.setattr(gridfs_service, "get_gridfs", lambda: bucket)

    await gridfs_service.delete_file("000000000000000000000003")

    assert bucket.deleted_id == ObjectId("000000000000000000000003")