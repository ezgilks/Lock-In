import os
import pathlib

TEST_DB = pathlib.Path(__file__).parent / "_test_lockin.db"
os.environ["DB_PATH"] = str(TEST_DB)

import pytest
from fastapi.testclient import TestClient

from main import app


def _remove_db_files():
    for suffix in ("", "-wal", "-shm"):
        pathlib.Path(str(TEST_DB) + suffix).unlink(missing_ok=True)


@pytest.fixture
def client():
    """Fresh schema + seeded dev user per test, via the app's real lifespan."""
    _remove_db_files()
    with TestClient(app) as c:
        yield c
    _remove_db_files()
