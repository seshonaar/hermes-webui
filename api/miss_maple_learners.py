"""Household learner selection bound to Hermes WebUI auth sessions."""

import importlib
import os
import re

_LEARNER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MAX_LEARNERS = 16


class LearnerSelectionError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def configured_learners() -> list[dict[str, str]]:
    raw = os.getenv("MISS_MAPLE_LEARNERS", "").strip()
    if not raw:
        raise LearnerSelectionError("Learner profiles are not configured", status=503)
    learners = []
    seen = set()
    for item in raw.split(","):
        learner_id, separator, display_name = item.partition(":")
        learner_id = learner_id.strip()
        display_name = display_name.strip()
        if (
            not separator
            or not _LEARNER_ID_RE.fullmatch(learner_id)
            or not display_name
            or len(display_name) > 80
            or any(character in display_name for character in "\r\n\x00")
        ):
            raise LearnerSelectionError("MISS_MAPLE_LEARNERS is invalid", status=503)
        if learner_id in seen:
            raise LearnerSelectionError(
                "MISS_MAPLE_LEARNERS contains duplicate ids", status=503
            )
        seen.add(learner_id)
        learners.append({"id": learner_id, "name": display_name})
        if len(learners) > _MAX_LEARNERS:
            raise LearnerSelectionError(
                "Too many learner profiles are configured", status=503
            )
    return learners


def session_learner(handler) -> dict[str, str] | None:
    auth = importlib.import_module("api.auth")
    cookie = auth.parse_cookie(handler)
    info = auth.get_session_info(cookie or "")
    learner_id = str((info or {}).get("learner_id") or "")
    return next(
        (learner for learner in configured_learners() if learner["id"] == learner_id),
        None,
    )


def learner_status(handler) -> dict:
    return {
        "learners": configured_learners(),
        "selected": session_learner(handler),
        "camera_mode": "job",
    }


def select_learner(handler, learner_id: object) -> dict:
    auth = importlib.import_module("api.auth")
    learner_id = str(learner_id or "")
    learner = next(
        (item for item in configured_learners() if item["id"] == learner_id),
        None,
    )
    if learner is None:
        raise LearnerSelectionError("Unknown learner profile")
    cookie = auth.parse_cookie(handler)
    if not auth.set_session_value(cookie or "", "learner_id", learner_id):
        raise LearnerSelectionError("Authenticated session is required", status=401)
    return {"learners": configured_learners(), "selected": learner}


def require_learner_id(handler) -> str:
    learner = session_learner(handler)
    if learner is None:
        raise LearnerSelectionError(
            "Select a learner before using Miss Maple", status=409
        )
    return learner["id"]
