import os
import uuid

import httpx
import pytest


BASE_URL = os.getenv("WAKUWAKU_API_BASE", "http://localhost:7000/v2")
WANIKANI_API_KEY = os.getenv("WANIKANI_TEST_API_KEY")


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=120.0)


@pytest.fixture(scope="session")
def auth_header(client: httpx.Client) -> dict[str, str]:
    email = f"compat-{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"
    username = f"compat-{uuid.uuid4().hex[:8]}"

    response = client.post("/auth/standalone/register", json={
        "email": email,
        "password": password,
        "username": username,
    })
    response.raise_for_status()
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def synced_auth_header(client: httpx.Client, auth_header: dict[str, str]) -> dict[str, str]:
    if not WANIKANI_API_KEY:
        pytest.skip("WANIKANI_TEST_API_KEY is not set")

    preflight = client.post("/sync/preflight", headers=auth_header, json={"api_key": WANIKANI_API_KEY})
    preflight.raise_for_status()

    sync = client.post("/sync", headers=auth_header, json={"api_key": WANIKANI_API_KEY, "mode": "merge"})
    sync.raise_for_status()
    payload = sync.json()
    assert payload["success"] is True
    assert payload["subjects_synced"] > 0
    return auth_header


def assert_collection_shape(payload: dict) -> None:
    assert payload["object"] == "collection"
    assert isinstance(payload["url"], str)
    assert isinstance(payload["data_updated_at"], str)
    assert "pages" in payload
    assert payload["pages"]["previous_url"] is None
    assert payload["pages"]["per_page"] == 500
    assert isinstance(payload["total_count"], int)
    assert isinstance(payload["data"], list)


def test_sync_preflight_reports_mismatches(client: httpx.Client, auth_header: dict[str, str]) -> None:
    if not WANIKANI_API_KEY:
        pytest.skip("WANIKANI_TEST_API_KEY is not set")

    response = client.post("/sync/preflight", headers=auth_header, json={"api_key": WANIKANI_API_KEY})
    response.raise_for_status()
    payload = response.json()

    assert "remote_user" in payload
    assert "local_user" in payload
    assert "server_data_counts" in payload
    assert payload["recommended_mode"] in {"merge", "overwrite"}
    assert isinstance(payload["warnings"], list)


def test_user_shape_after_sync(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    response = client.get("/user", headers=synced_auth_header)
    response.raise_for_status()
    payload = response.json()

    assert payload["object"] == "user"
    assert isinstance(payload["data"]["username"], str)
    assert isinstance(payload["data"]["level"], int)
    assert "subscription" in payload["data"]


def test_assignments_collection_and_filters(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    response = client.get("/assignments", headers=synced_auth_header)
    response.raise_for_status()
    payload = response.json()

    assert_collection_shape(payload)
    assert payload["total_count"] > 0

    first = payload["data"][0]
    filtered = client.get(
        "/assignments",
        headers=synced_auth_header,
        params={"subject_ids": str(first["data"]["subject_id"])}
    )
    filtered.raise_for_status()
    filtered_payload = filtered.json()
    assert filtered_payload["total_count"] >= 1
    assert all(item["data"]["subject_id"] == first["data"]["subject_id"] for item in filtered_payload["data"])
    assert "user_id" not in first["data"]


def test_review_statistics_collection_and_filters(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    response = client.get("/review_statistics", headers=synced_auth_header)
    response.raise_for_status()
    payload = response.json()

    assert_collection_shape(payload)
    assert payload["total_count"] > 0

    first = payload["data"][0]
    filtered = client.get(
        "/review_statistics",
        headers=synced_auth_header,
        params={"subject_ids": str(first["data"]["subject_id"])}
    )
    filtered.raise_for_status()
    filtered_payload = filtered.json()
    assert filtered_payload["total_count"] >= 1
    assert all(item["data"]["subject_id"] == first["data"]["subject_id"] for item in filtered_payload["data"])
    assert "user_id" not in first["data"]


def test_subjects_collection_shape(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    response = client.get("/subjects", headers=synced_auth_header)
    response.raise_for_status()
    payload = response.json()

    assert_collection_shape(payload)
    assert payload["total_count"] > 0

    first = payload["data"][0]
    assert first["object"] in {"radical", "kanji", "vocabulary", "kana_vocabulary"}
    assert isinstance(first["data"]["slug"], str)
    assert isinstance(first["data"]["level"], int)
    assert "user_id" not in first["data"]


def test_level_progressions_and_summary_shape(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    progressions = client.get("/level_progressions", headers=synced_auth_header)
    progressions.raise_for_status()
    progressions_payload = progressions.json()
    assert_collection_shape(progressions_payload)

    summary = client.get("/summary", headers=synced_auth_header)
    summary.raise_for_status()
    summary_payload = summary.json()
    assert summary_payload["object"] == "report"
    assert "lessons" in summary_payload["data"]
    assert "reviews" in summary_payload["data"]
    assert "next_reviews_at" in summary_payload["data"]


def test_study_material_create_and_update_shape(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    subjects = client.get("/subjects", headers=synced_auth_header)
    subjects.raise_for_status()
    subject_id = subjects.json()["data"][0]["id"]

    created = client.post("/study_materials", headers=synced_auth_header, json={
        "study_material": {
            "subject_id": subject_id,
            "meaning_note": "compat note",
            "reading_note": "compat reading",
            "meaning_synonyms": ["compat synonym"],
        }
    })
    created.raise_for_status()
    created_payload = created.json()

    assert created_payload["object"] == "study_material"
    assert created_payload["data"]["subject_id"] == subject_id
    assert created_payload["data"]["meaning_note"] == "compat note"
    assert created_payload["data"]["meaning_synonyms"] == ["compat synonym"]
    assert "user_id" not in created_payload["data"]

    updated = client.put(f"/study_materials/{created_payload['id']}", headers=synced_auth_header, json={
        "study_material": {
            "meaning_note": "updated compat note",
            "reading_note": "updated compat reading",
            "meaning_synonyms": ["updated synonym"],
        }
    })
    updated.raise_for_status()
    updated_payload = updated.json()

    assert updated_payload["data"]["meaning_note"] == "updated compat note"
    assert updated_payload["data"]["reading_note"] == "updated compat reading"
    assert updated_payload["data"]["meaning_synonyms"] == ["updated synonym"]


def test_assignment_start_and_review_create_shapes(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    assignments = client.get(
        "/assignments",
        headers=synced_auth_header,
        params={"started": "false", "immediately_available_for_lessons": "true"},
    )
    assignments.raise_for_status()
    payload = assignments.json()
    assert payload["total_count"] > 0
    assignment_id = payload["data"][0]["id"]

    started = client.put(
        f"/assignments/{assignment_id}/start",
        headers=synced_auth_header,
        json={"started_at": "2026-04-18T12:00:00.000000Z"},
    )
    started.raise_for_status()
    started_payload = started.json()
    assert started_payload["object"] == "assignment"
    assert started_payload["id"] == assignment_id
    assert started_payload["data"]["started_at"] is not None
    assert "user_id" not in started_payload["data"]

    review = client.post(
        "/reviews",
        headers=synced_auth_header,
        json={
            "review": {
                "assignment_id": assignment_id,
                "incorrect_meaning_answers": 0,
                "incorrect_reading_answers": 0,
                "created_at": "2026-04-18T12:05:00.000000Z",
            }
        },
    )
    review.raise_for_status()
    review_payload = review.json()

    assert review_payload["object"] == "review"
    assert review_payload["data"]["assignment_id"] == assignment_id
    assert "resources_updated" in review_payload
    assert review_payload["resources_updated"]["assignment"]["object"] == "assignment"
    assert review_payload["resources_updated"]["review_statistic"]["object"] == "review_statistic"
    assert "user_id" not in review_payload["resources_updated"]["assignment"]["data"]
    assert "user_id" not in review_payload["resources_updated"]["review_statistic"]["data"]


def test_spaced_repetition_systems_shape(client: httpx.Client, synced_auth_header: dict[str, str]) -> None:
    response = client.get("/spaced_repetition_systems", headers=synced_auth_header)
    response.raise_for_status()
    payload = response.json()

    assert_collection_shape(payload)
    assert payload["total_count"] >= 1
    first = payload["data"][0]
    assert first["object"] == "spaced_repetition_system"
    assert isinstance(first["data"]["name"], str)
    assert isinstance(first["data"]["stages"], list)
