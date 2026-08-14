import pytest
from tests.core.client import RuoyiApiClient


@pytest.fixture(scope="session")
def api_client():
    return RuoyiApiClient("http://localhost:18080")


@pytest.fixture(scope="session")
def auth_token(api_client):
    token = api_client.login_and_get_token()
    return token


@pytest.fixture(scope="session")
def auth_headers(api_client, auth_token):
    if auth_token:
        return api_client.set_auth_header(auth_token)
    return {}


@pytest.fixture(scope="function")
def no_auth_headers():
    return {}


@pytest.fixture(scope="function")
def invalid_token_headers():
    return {"Authorization": "Bearer invalid_token_12345"}


@pytest.fixture(scope="function")
def expired_token_headers():
    return {"Authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.expired_token_for_test"}