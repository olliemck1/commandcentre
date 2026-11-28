import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

@pytest.fixture(autouse=True)
def client():
    headers = {}
    if settings.APP_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.APP_ACCESS_TOKEN}"
    with TestClient(app, headers=headers) as c:
        yield c
