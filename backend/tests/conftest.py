import os
import sys
from contextlib import contextmanager

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")
os.environ["DATABASE_URL"] = ""


class FakeCursor:
    def __init__(self, rows=None, one=None):
        self._rows = rows or []
        self._one = one

    def execute(self, query, *args):
        q = query.lower()
        if "from users where email" in q and "password" in q:
            self._one = None
        elif "from users where verification_token" in q:
            self._one = None
        elif "count(*) from diseases" in q:
            self._one = (0,)
        elif "from diseases" in q and "order by" in q:
            self._rows = []
        return None

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._rows

    def executemany(self, query, args):
        return None

    @property
    def description(self):
        return [("id",), ("crop",)]


class FakeConn:
    _is_mysql = False

    def cursor(self):
        return FakeCursor()

    def commit(self):
        pass

    def close(self):
        pass


@contextmanager
def fake_get_db():
    yield FakeConn()


@pytest.fixture(autouse=True)
def mock_database(monkeypatch):
    import main

    monkeypatch.setattr(main, "get_db", fake_get_db)
