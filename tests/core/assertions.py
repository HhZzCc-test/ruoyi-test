import allure


def assert_http_ok(resp, msg=None):
    if msg is None:
        msg = f"HTTP status: {resp.status_code}, body: {resp.text}"
    assert resp.status_code == 200, msg


def assert_business_success(data, msg=None):
    code = data.get("code")
    if msg is None:
        msg = f"business success: {code}, msg: {data.get('msg')}"
    assert code == 200, msg


def assert_business_error(data, msg=None):
    code = data.get("code")
    if msg is None:
        msg = f"business error: {data}"
    assert code != 200, msg


def assert_field_exists(data, field, msg=None):
    if msg is None:
        msg = f"field not exists: {field}"
    assert field in data, msg


def assert_field_not_empty(data, field, msg=None):
    value = data.get(field)
    if msg is None:
        msg = f"field {field} empty"
    assert value is not None and value != "", msg


def assert_field_type(data, field, expected_type, msg=None):
    value = data.get(field)
    if msg is None:
        msg = f"field {field} type: expected {expected_type}, actual {type(value)}"
    assert isinstance(value, expected_type), msg


def assert_response_time(elapsed, max_seconds=3.0, msg=None):
    if msg is None:
        msg = f"response time: {elapsed:.2f}s, expected < {max_seconds}s"
    assert elapsed < max_seconds, msg
    allure.attach(str(elapsed), "response time(s)", allure.attachment_type.TEXT)


def assert_all_unique(items, msg=None):
    if msg is None:
        msg = f"items not unique: {items}"
    assert len(set(items)) == len(items), msg