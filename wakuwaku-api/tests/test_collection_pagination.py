from app.services.wakuwaku_service import WakuWakuService


def make_service() -> WakuWakuService:
    return WakuWakuService(supabase_client=None, user_id="test-user")


def test_paginate_rows_builds_next_and_previous_urls() -> None:
    service = make_service()
    rows = [{"id": idx} for idx in range(1200)]

    page_rows, next_url, previous_url, total_count = service._paginate_rows(
        rows,
        "/assignments",
        page_after=500,
        per_page=500,
        params={"updated_after": "2026-04-18T00:00:00Z", "subject_ids": [1, 2]},
    )

    assert len(page_rows) == 500
    assert page_rows[0]["id"] == 500
    assert page_rows[-1]["id"] == 999
    assert total_count == 1200
    assert next_url == "/v2/assignments?updated_after=2026-04-18T00%3A00%3A00Z&subject_ids=1&subject_ids=2&page_after=1000&per_page=500"
    assert previous_url == "/v2/assignments?updated_after=2026-04-18T00%3A00%3A00Z&subject_ids=1&subject_ids=2&page_after=0&per_page=500"


def test_paginate_rows_caps_page_size_and_omits_next_url_on_last_page() -> None:
    service = make_service()
    rows = [{"id": idx} for idx in range(10)]

    page_rows, next_url, previous_url, total_count = service._paginate_rows(
        rows,
        "/reviews",
        page_after=0,
        per_page=999,
    )

    assert len(page_rows) == 10
    assert total_count == 10
    assert next_url is None
    assert previous_url is None
