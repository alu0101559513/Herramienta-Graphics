import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from bson import ObjectId
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

os.environ["ENVIRONMENT"] = "test"
os.environ["MONGODB_URI"] = os.getenv("TEST_MONGODB_URI", "mongodb://localhost:27017")
os.environ["MONGODB_DB_NAME"] = os.getenv("TEST_MONGODB_DB_NAME", "app_test")
os.environ["MONGO_DB_NAME"] = os.getenv("TEST_MONGODB_DB_NAME", "app_test")
os.environ["DATABASE_NAME"] = os.getenv("TEST_MONGODB_DB_NAME", "app_test")
os.environ["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "test-secret-key")
os.environ["SECRET_KEY"] = os.getenv("SECRET_KEY", "test-secret-key")

import server.core.security as _sec
from server.db.database import init_db
from server.dependencies.auth import get_authenticated_user
from server.main import app

_sec.create_access_token = lambda subject, expires_delta=None: f"token-for-{subject}"
_sec.hash_password = lambda password: f"hashed:{password}"
_sec.verify_password = lambda password, hashed: hashed == f"hashed:{password}"

hash_password = _sec.hash_password


class _FieldProxy:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: object) -> tuple:
        return ("eq", self.name, other)

    def __ne__(self, other: object) -> tuple:
        return ("ne", self.name, other)


def _matches(obj: Any, conditions: tuple) -> bool:
    for condition in conditions:
        if not isinstance(condition, tuple):
            continue

        op, field, value = condition
        current = getattr(obj, field, None)

        if op == "eq" and current != value:
            return False

        if op == "ne" and current == value:
            return False

    return True


class _QueryResult:
    def __init__(self, items: list):
        self.items = items

    async def to_list(self):
        return self.items


class TestUser:
    users: list["TestUser"] = []

    username = _FieldProxy("username")
    email = _FieldProxy("email")
    id = _FieldProxy("id")

    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        created_at=None,
    ):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.now(timezone.utc)
        self.id = str(ObjectId())
        self.saved = False
        self.deleted = False

    @classmethod
    async def find_one(cls, *conditions, **kwargs):
        for user in cls.users:
            if user.deleted:
                continue

            if conditions and not _matches(user, conditions):
                continue

            if any(getattr(user, key, None) != value for key, value in kwargs.items()):
                continue

            return user

        return None

    async def insert(self):
        TestUser.users.append(self)
        self.saved = True
        return self

    async def save(self):
        self.saved = True
        return self

    async def delete(self):
        self.deleted = True
        try:
            TestUser.users.remove(self)
        except ValueError:
            pass


class TestAnalysis:
    analyses: list["TestAnalysis"] = []

    user_id = _FieldProxy("user_id")
    id = _FieldProxy("id")

    def __init__(self, **kwargs):
        self.id = str(ObjectId())
        self.user_id = None
        self.name = None
        self.description = None
        self.raw_dataset_file_id = None
        self.normalized_dataset_file_id = None
        self.metrics_config_file_id = None
        self.filtered_dataset_file_ids = {}
        self.dataset_capabilities = None
        self.algorithms = []
        self.problems = []
        self.metrics = []
        self.metrics_direction = {}
        self.plot_export_formats = ["png"]
        self.outputs = {}
        self.enabled_modules = []
        self.num_runs = 0
        self.evolution_metadata = {}
        self.selected_algorithms_last_run = []
        self.current_run_key = "all"
        self.status = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.saved = False
        self.deleted = False

        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    async def get(cls, analysis_id):
        analysis_id = str(analysis_id)

        for analysis in cls.analyses:
            if str(analysis.id) == analysis_id and not analysis.deleted:
                return analysis

        return None

    @classmethod
    def find(cls, *conditions, **kwargs):
        items = []

        for analysis in cls.analyses:
            if analysis.deleted:
                continue

            if conditions and not _matches(analysis, conditions):
                continue

            if any(
                getattr(analysis, key, None) != value
                for key, value in kwargs.items()
            ):
                continue

            items.append(analysis)

        return _QueryResult(items)

    async def insert(self):
        TestAnalysis.analyses.append(self)
        self.saved = True
        return self

    async def save(self):
        self.saved = True
        return self

    async def delete(self):
        self.deleted = True
        try:
            TestAnalysis.analyses.remove(self)
        except ValueError:
            pass


TEST_MONGODB_URI = os.environ["MONGODB_URI"]
TEST_MONGODB_DB_NAME = os.environ["MONGODB_DB_NAME"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def start_test_mongo():
    if os.getenv("CI") == "true":
        yield
        return

    subprocess.run(
        ["docker", "compose", "up", "-d", "mongo"],
        cwd=PROJECT_ROOT,
        check=True,
    )

    yield

@pytest.fixture(scope="session")
def mongo_uri() -> str:
    return TEST_MONGODB_URI


@pytest.fixture(scope="session")
def mongo_db_name() -> str:
    return TEST_MONGODB_DB_NAME


@pytest_asyncio.fixture
async def mongo_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    client = AsyncIOMotorClient(TEST_MONGODB_URI)
    try:
        yield client
    finally:
        client.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_beanie_session(start_test_mongo):
    await init_db()
    yield


@pytest_asyncio.fixture(autouse=True)
async def clean_mongodb(mongo_client: AsyncIOMotorClient):
    db = mongo_client[TEST_MONGODB_DB_NAME]

    TestUser.users.clear()
    TestAnalysis.analyses.clear()

    await db.users.delete_many({})
    await db.analyses.delete_many({})
    await db.fs.files.delete_many({})
    await db.fs.chunks.delete_many({})

    yield

    TestUser.users.clear()
    TestAnalysis.analyses.clear()

    await db.users.delete_many({})
    await db.analyses.delete_many({})
    await db.fs.files.delete_many({})
    await db.fs.chunks.delete_many({})


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    import server.routers.analysis as analysis_routes
    import server.routers.auth as auth_routes

    auth_routes.User = TestUser
    auth_routes.Analysis = TestAnalysis
    auth_routes.hash_password = lambda password: f"hashed:{password}"
    auth_routes.create_access_token = (
        lambda subject, expires_delta=None: f"token-for-{subject}"
    )
    auth_routes.verify_password = (
        lambda password, hashed: hashed == f"hashed:{password}"
    )

    analysis_routes.Analysis = TestAnalysis

    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def test_user() -> TestUser:
    user = TestUser(
        username="testuser",
        email="testuser@example.com",
        password_hash=hash_password("Secret123!"),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    await user.insert()
    return user


@pytest.fixture
def authenticated_test_user(test_user: TestUser) -> TestUser:
    async def override_get_authenticated_user():
        return test_user

    app.dependency_overrides[get_authenticated_user] = override_get_authenticated_user
    return test_user


@pytest_asyncio.fixture
async def test_analysis(authenticated_test_user: TestUser) -> TestAnalysis:
    analysis = TestAnalysis(
        user_id=authenticated_test_user.id,
        name="Main Analysis",
        description="Main description",
        raw_dataset_file_id="raw-file-id",
        normalized_dataset_file_id="normalized-file-id",
        metrics_config_file_id="metrics-file-id",
        filtered_dataset_file_ids={"all": "filtered-file-id"},
        dataset_capabilities={
            "saes_plots": True,
            "saes_reports": True,
            "notebooks": True,
            "evolution_plots": True,
        },
        algorithms=["A1", "A2"],
        problems=["P1"],
        metrics=["Accuracy"],
        metrics_direction={"Accuracy": "maximize"},
        plot_export_formats=["png"],
        outputs={
            "saes_plots": {"plot.png": "plot-file-id"},
            "saes_reports": {"report.tex": "report-file-id"},
            "notebooks": {"analysis.ipynb": "notebook-file-id"},
            "evolution_plots": {"evolution.svg": "evolution-file-id"},
            "analysis_runs": {
                "all": {
                    "selected_algorithms": ["A1", "A2"],
                    "modules": ["saes_plots"],
                    "saes_plots": {"plot.png": "plot-file-id"},
                }
            },
        },
        enabled_modules=["saes_plots"],
        num_runs=1,
        evolution_metadata={},
        selected_algorithms_last_run=["A1", "A2"],
        current_run_key="all",
        status="completed",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    await analysis.insert()
    return analysis