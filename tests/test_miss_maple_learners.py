import importlib
from types import SimpleNamespace


def test_learner_selection_is_bound_to_the_authenticated_session(monkeypatch):
    auth = importlib.import_module("api.auth")
    from api import miss_maple_learners as learners

    monkeypatch.setenv("MISS_MAPLE_LEARNERS", "ana:Ana,matei:Matei")
    sessions = {"cookie-a": {}, "cookie-b": {}}
    monkeypatch.setattr(auth, "parse_cookie", lambda handler: handler.cookie)
    monkeypatch.setattr(auth, "get_session_info", lambda cookie: sessions.get(cookie))
    monkeypatch.setattr(
        auth,
        "set_session_value",
        lambda cookie, key, value: sessions[cookie].update({key: value}) is None,
    )

    first = SimpleNamespace(cookie="cookie-a")
    second = SimpleNamespace(cookie="cookie-b")
    assert learners.learner_status(first)["selected"] is None
    assert learners.select_learner(first, "ana")["selected"]["name"] == "Ana"
    assert learners.require_learner_id(first) == "ana"
    assert learners.learner_status(second)["selected"] is None


def test_camera_always_uses_the_rust_ocr_job(monkeypatch):
    from api import miss_maple_learners as learners

    monkeypatch.setenv("MISS_MAPLE_LEARNERS", "ana:Ana")
    monkeypatch.setattr(learners, "session_learner", lambda _handler: None)
    assert learners.learner_status(object())["camera_mode"] == "job"


def test_invalid_or_duplicate_learner_configuration_fails_closed(monkeypatch):
    from api import miss_maple_learners as learners

    monkeypatch.setenv("MISS_MAPLE_LEARNERS", "ana:Ana,ana:Other")
    try:
        learners.configured_learners()
    except learners.LearnerSelectionError as error:
        assert error.status == 503
    else:
        raise AssertionError("duplicate learners must be rejected")
