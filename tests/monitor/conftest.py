import pytest
from tests.core.client import RuoyiApiClient


@pytest.fixture(scope="session")
def api_client():
    client = RuoyiApiClient("http://localhost:18080")
    return client


@pytest.fixture(scope="session")
def auth_headers(api_client):
    token = api_client.login_and_get_token("admin", "admin123")
    if token:
        api_client.set_auth_header(token)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def auth_token(api_client, auth_headers):
    return auth_headers.get("Authorization", "").replace("Bearer ", "")


@pytest.fixture(autouse=True)
def _monitor_auth_setup(api_client, auth_headers, request):
    if request.cls:
        request.cls.client = api_client
