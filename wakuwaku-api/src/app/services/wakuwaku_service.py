import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union, Dict, Any
from urllib.parse import urlencode
from app.core.config import settings

logger = logging.getLogger(__name__)

WKID = Union[int, str]
SYSTEM_SUBJECT_USER_ID = "00000000-0000-0000-0000-000000000000"
LEGACY_TEMPLATE_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_SRS_ID = 1
DEFAULT_COLLECTION_PAGE_SIZE = 500

FALLBACK_SYSTEM_SUBJECTS = [
    {
        "id": 1,
        "type": "radical",
        "slug": "ground",
        "level": 1,
        "characters": "一",
        "meaning_mnemonic": "A single line can represent the ground beneath your feet.",
        "meanings": [{"meaning": "ground", "primary": True, "accepted_answer": True}],
        "readings": [],
        "auxiliary_meanings": [],
        "component_subject_ids": [],
        "amalgamation_subject_ids": [],
        "visually_similar_subject_ids": [],
        "context_sentences": [],
        "pronunciation_audios": [],
        "character_images": [],
        "parts_of_speech": [],
        "lesson_position": 1,
        "spaced_repetition_system_id": DEFAULT_SRS_ID,
    },
    {
        "id": 440,
        "type": "kanji",
        "slug": "one",
        "level": 1,
        "characters": "一",
        "meaning_mnemonic": "One straight stroke is the kanji for one.",
        "reading_mnemonic": "Imagine saying ichi after counting the first point.",
        "meanings": [{"meaning": "one", "primary": True, "accepted_answer": True}],
        "readings": [{"reading": "いち", "primary": True, "accepted_answer": True, "type": "onyomi"}],
        "auxiliary_meanings": [],
        "component_subject_ids": [1],
        "amalgamation_subject_ids": [],
        "visually_similar_subject_ids": [],
        "context_sentences": [],
        "pronunciation_audios": [],
        "character_images": [],
        "parts_of_speech": [],
        "lesson_position": 2,
        "spaced_repetition_system_id": DEFAULT_SRS_ID,
    },
    {
        "id": 10000,
        "type": "vocabulary",
        "slug": "one-day",
        "level": 1,
        "characters": "一日",
        "meaning_mnemonic": "A single day is one day.",
        "reading_mnemonic": "Read this as いちにち for one whole day.",
        "meanings": [{"meaning": "one day", "primary": True, "accepted_answer": True}],
        "readings": [{"reading": "いちにち", "primary": True, "accepted_answer": True}],
        "auxiliary_meanings": [],
        "component_subject_ids": [440],
        "amalgamation_subject_ids": [],
        "visually_similar_subject_ids": [],
        "context_sentences": [],
        "pronunciation_audios": [],
        "character_images": [],
        "parts_of_speech": ["noun"],
        "lesson_position": 3,
        "spaced_repetition_system_id": DEFAULT_SRS_ID,
    },
]

class WakuWakuService:
    def __init__(self, supabase_client, user_id: str):
        self.client = supabase_client
        self.user_id = user_id
        # Use v2 prefix by default since the routes are v2
        self.base_url = f"{settings.API_V1_STR}" 

    def _format_object(self, data: dict, object_type: str, url_prefix: str) -> dict:
        obj_id = data.get("id") or data.get("wanikani_id") or data.get("ku_id")
        # Ensure ID is string for consistency in the root, although WK usually uses ints
        # But we need to handle UUIDs too.
        str_id = str(obj_id) if obj_id else "0"
        
        if "data" in data and isinstance(data["data"], dict):
            inner = data["data"]
        else:
            inner = self._serialize_inner_data(data, object_type)

        return {
            "id": obj_id, # Keep as native type (int if possible) for frontend compatibility
            "object": object_type,
            "url": f"{self.base_url}{url_prefix}/{str_id}",
            "data_updated_at": self._format_date(data.get("data_updated_at") or data.get("updated_at") or datetime.utcnow()),
            "data": inner
        }

    def _serialize_inner_data(self, data: dict, object_type: str) -> dict:
        if object_type == "assignment":
            return {
                "available_at": self._format_date(data.get("available_at")),
                "burned_at": self._format_date(data.get("burned_at")),
                "created_at": self._format_date(data.get("created_at")),
                "hidden": data.get("hidden", False),
                "passed_at": self._format_date(data.get("passed_at")),
                "resurrected_at": self._format_date(data.get("resurrected_at")),
                "srs_stage": data.get("srs_stage", 0),
                "started_at": self._format_date(data.get("started_at")),
                "subject_id": data.get("subject_id"),
                "subject_type": data.get("subject_type"),
                "unlocked_at": self._format_date(data.get("unlocked_at")),
            }
        if object_type == "review":
            return {
                "created_at": self._format_date(data.get("created_at")),
                "assignment_id": data.get("assignment_id"),
                "spaced_repetition_system_id": data.get("spaced_repetition_system_id", DEFAULT_SRS_ID),
                "subject_id": data.get("subject_id"),
                "starting_srs_stage": data.get("starting_srs_stage", 0),
                "ending_srs_stage": data.get("ending_srs_stage", 0),
                "incorrect_meaning_answers": data.get("incorrect_meaning_answers", 0),
                "incorrect_reading_answers": data.get("incorrect_reading_answers", 0),
            }
        if object_type == "review_statistic":
            return {
                "created_at": self._format_date(data.get("created_at")),
                "hidden": data.get("hidden", False),
                "meaning_correct": data.get("meaning_correct", 0),
                "meaning_current_streak": data.get("meaning_current_streak", 0),
                "meaning_incorrect": data.get("meaning_incorrect", 0),
                "meaning_max_streak": data.get("meaning_max_streak", 0),
                "reading_correct": data.get("reading_correct", 0),
                "reading_current_streak": data.get("reading_current_streak", 0),
                "reading_incorrect": data.get("reading_incorrect", 0),
                "reading_max_streak": data.get("reading_max_streak", 0),
                "percentage_correct": data.get("percentage_correct", 0),
                "subject_id": data.get("subject_id"),
                "subject_type": data.get("subject_type"),
            }
        if object_type == "level_progression":
            return {
                "level": data.get("level"),
                "created_at": self._format_date(data.get("created_at")),
                "unlocked_at": self._format_date(data.get("unlocked_at")),
                "started_at": self._format_date(data.get("started_at")),
                "passed_at": self._format_date(data.get("passed_at")),
                "completed_at": self._format_date(data.get("completed_at")),
                "abandoned_at": self._format_date(data.get("abandoned_at")),
            }
        if object_type == "study_material":
            return {
                "created_at": self._format_date(data.get("created_at")),
                "hidden": data.get("hidden", False),
                "meaning_note": data.get("meaning_note"),
                "meaning_synonyms": data.get("meaning_synonyms") or [],
                "reading_note": data.get("reading_note"),
                "subject_id": data.get("subject_id"),
                "subject_type": data.get("subject_type"),
            }
        if object_type == "reset":
            return {
                "created_at": self._format_date(data.get("created_at")),
                "original_level": data.get("original_level"),
                "target_level": data.get("target_level"),
                "confirmed_at": self._format_date(data.get("confirmed_at")),
            }
        if object_type == "spaced_repetition_system":
            return {
                "created_at": self._format_date(data.get("created_at")),
                "name": data.get("name"),
                "description": data.get("description"),
                "unlocking_stage_position": data.get("unlocking_stage_position", 0),
                "starting_stage_position": data.get("starting_stage_position", 1),
                "passing_stage_position": data.get("passing_stage_position", 5),
                "burning_stage_position": data.get("burning_stage_position", 9),
                "stages": data.get("stages") or [],
            }
        if object_type in {"radical", "kanji", "vocabulary", "kana_vocabulary"}:
            base = {
                "auxiliary_meanings": data.get("auxiliary_meanings") or [],
                "characters": data.get("characters"),
                "created_at": self._format_date(data.get("created_at")),
                "document_url": data.get("document_url"),
                "hidden_at": self._format_date(data.get("hidden_at")),
                "lesson_position": data.get("lesson_position", 0),
                "level": data.get("level", 1),
                "meaning_mnemonic": data.get("meaning_mnemonic"),
                "meanings": data.get("meanings") or [],
                "slug": data.get("slug"),
                "spaced_repetition_system_id": data.get("spaced_repetition_system_id", DEFAULT_SRS_ID),
            }
            if object_type == "radical":
                base["amalgamation_subject_ids"] = data.get("amalgamation_subject_ids") or []
                base["character_images"] = data.get("character_images") or []
                return base
            if object_type == "kanji":
                base["amalgamation_subject_ids"] = data.get("amalgamation_subject_ids") or []
                base["component_subject_ids"] = data.get("component_subject_ids") or []
                base["meaning_hint"] = data.get("meaning_hint")
                base["reading_hint"] = data.get("reading_hint")
                base["reading_mnemonic"] = data.get("reading_mnemonic")
                base["readings"] = data.get("readings") or []
                base["visually_similar_subject_ids"] = data.get("visually_similar_subject_ids") or []
                return base
            if object_type == "vocabulary":
                base["component_subject_ids"] = data.get("component_subject_ids") or []
                base["context_sentences"] = data.get("context_sentences") or []
                base["parts_of_speech"] = data.get("parts_of_speech") or []
                base["pronunciation_audios"] = data.get("pronunciation_audios") or []
                base["readings"] = data.get("readings") or []
                base["reading_mnemonic"] = data.get("reading_mnemonic")
                return base
            if object_type == "kana_vocabulary":
                base["context_sentences"] = data.get("context_sentences") or []
                base["parts_of_speech"] = data.get("parts_of_speech") or []
                base["pronunciation_audios"] = data.get("pronunciation_audios") or []
                return base

        filtered = data.copy()
        for key in ["id", "object", "url", "data_updated_at", "updated_at", "type", "ku_id", "user_id"]:
            filtered.pop(key, None)
        return filtered

    def _parse_csv_ids(self, ids: Optional[Union[str, List[Union[str, int]]]]) -> Optional[List[int]]:
        if ids is None:
            return None
        if isinstance(ids, list):
            values = ids
        else:
            values = [part.strip() for part in str(ids).split(",") if part.strip()]
        parsed: List[int] = []
        for value in values:
            try:
                parsed.append(int(value))
            except (TypeError, ValueError):
                continue
        return parsed or None

    def _apply_updated_after_filter(self, rows: List[dict], updated_after: Optional[datetime]) -> List[dict]:
        if not updated_after:
            return rows
        threshold = updated_after.isoformat()
        return [
            row for row in rows
            if (row.get("updated_at") or row.get("created_at") or "") >= threshold
        ]

    def _apply_ids_filter(self, rows: List[dict], ids: Optional[Union[str, List[Union[str, int]]]]) -> List[dict]:
        parsed = self._parse_csv_ids(ids)
        if not parsed:
            return rows
        allowed = set(parsed)
        return [row for row in rows if int(row.get("id") or 0) in allowed]

    def _apply_field_ids_filter(
        self,
        rows: List[dict],
        field_name: str,
        ids: Optional[Union[str, List[Union[str, int]]]]
    ) -> List[dict]:
        parsed = self._parse_csv_ids(ids)
        if not parsed:
            return rows
        allowed = set(parsed)
        return [row for row in rows if int(row.get(field_name) or 0) in allowed]

    def _normalize_query_params(self, params: Dict[str, Any]) -> Dict[str, List[str]]:
        normalized: Dict[str, List[str]] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, datetime):
                normalized[key] = [value.isoformat()]
                continue
            if isinstance(value, (list, tuple)):
                values = []
                for item in value:
                    if item is None:
                        continue
                    if isinstance(item, datetime):
                        values.append(item.isoformat())
                    else:
                        values.append(str(item))
                if values:
                    normalized[key] = values
                continue
            normalized[key] = [str(value)]
        return normalized

    def _build_collection_url(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        normalized = self._normalize_query_params(params or {})
        query = urlencode([(key, value) for key, values in normalized.items() for value in values], doseq=True)
        if query:
            return f"{self.base_url}{path}?{query}"
        return f"{self.base_url}{path}"

    def _paginate_rows(
        self,
        rows: List[dict],
        path: str,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        params: Optional[Dict[str, Any]] = None
    ) -> tuple[List[dict], Optional[str], Optional[str], int]:
        safe_per_page = max(1, min(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), DEFAULT_COLLECTION_PAGE_SIZE))
        safe_page_after = max(int(page_after or 0), 0)
        total_count = len(rows)

        page_rows = rows[safe_page_after:safe_page_after + safe_per_page]

        next_url: Optional[str] = None
        if safe_page_after + safe_per_page < total_count:
            next_params = dict(params or {})
            next_params.update({
                "page_after": safe_page_after + safe_per_page,
                "per_page": safe_per_page,
            })
            next_url = self._build_collection_url(path, next_params)

        previous_url: Optional[str] = None
        if safe_page_after > 0:
            previous_params = dict(params or {})
            previous_params.update({
                "page_after": max(safe_page_after - safe_per_page, 0),
                "per_page": safe_per_page,
            })
            previous_url = self._build_collection_url(path, previous_params)

        return page_rows, next_url, previous_url, total_count

    async def get_user(self) -> dict:
        result = self.client.table("users").select("*").eq("id", self.user_id).execute()
        if not result.data:
            # Automatic seeding if no user found (needed for standalone and WK hybrid modes)
            user_data = await self.seed_standalone_user()
        else:
            user_data = result.data[0]
        await self.ensure_user_learning_state(user_data)
            
        return {
            "id": user_data.get("id"),
            "object": "user",
            "url": f"{self.base_url}/user",
            "data_updated_at": self._format_date(user_data.get("updated_at") or datetime.utcnow()),
            "data": {
                "id": str(user_data.get("id")),
                "username": user_data.get("username") or "HanaUser",
                "level": user_data.get("level") or 1,
                "profile_url": (
                    f"https://www.wanikani.com/users/{user_data.get('username')}"
                    if user_data.get("username")
                    else f"{self.base_url}/user"
                ),
                "started_at": self._format_date(user_data.get("created_at") or user_data.get("started_at")),
                "subscription": {
                    "active": (user_data.get("subscription_type") or "free") not in {"free", "unknown"},
                    "max_level_granted": user_data.get("max_level_granted") or 60,
                    "period_ends_at": self._format_date(user_data.get("subscription_ends_at")),
                    "type": user_data.get("subscription_type") or "free"
                },
                "current_vacation_started_at": None
            }
        }

    async def seed_standalone_user(self) -> dict:
        """Initialize a new user's level and settings in the local database."""
        now = datetime.utcnow().isoformat()
        insert_data = {
            "id": self.user_id,
            "level": 1,
            "username": "User",
            "created_at": now,
            "updated_at": now
        }
        result = self.client.table("users").upsert(insert_data, on_conflict="id").execute()
        if not result.data:
            # Could already exist, fetch then
            return await self.get_user()
        return result.data[0]

    async def ensure_user_learning_state(self, user_data: Optional[dict] = None) -> None:
        if not user_data:
            user_res = self.client.table("users").select("*").eq("id", self.user_id).limit(1).execute()
            if not user_res.data:
                user_data = await self.seed_standalone_user()
            else:
                user_data = user_res.data[0]

        now = datetime.utcnow()
        now_iso = now.isoformat()
        await self._ensure_level_progression(user_data, now_iso, now_iso)
        await self._sync_unlocked_assignments(user_data, now)

    async def _ensure_assignments_for_subjects(self, subjects: List[dict], now: str, unlocked_at: str) -> None:
        if not subjects:
            return

        subject_ids = [subject["id"] for subject in subjects]
        existing_assignments_res = self.client.table("assignments") \
            .select("subject_id") \
            .eq("user_id", self.user_id) \
            .in_("subject_id", subject_ids) \
            .execute()
        existing_subject_ids = {row["subject_id"] for row in (existing_assignments_res.data or [])}

        missing_subjects = [subject for subject in subjects if subject["id"] not in existing_subject_ids]
        if not missing_subjects:
            return

        next_assignment_id = await self._next_table_id("assignments")
        assignment_rows = []
        for offset, subject in enumerate(missing_subjects):
            assignment_rows.append({
                "id": next_assignment_id + offset,
                "user_id": self.user_id,
                "subject_id": subject["id"],
                "subject_type": subject["type"],
                "level": subject["level"],
                "srs_stage": 0,
                "unlocked_at": unlocked_at,
                "available_at": unlocked_at,
                "hidden": False,
                "created_at": now,
                "updated_at": now,
            })
        self.client.table("assignments").insert(assignment_rows).execute()

    async def _ensure_level_progression(self, user_data: dict, now: str, unlocked_at: str) -> None:
        level = max(int(user_data.get("level") or 1), 1)
        progression = self.client.table("level_progressions").select("id").eq("user_id", self.user_id).eq("level", level).limit(1).execute()
        if progression.data:
            return

        next_progression_id = await self._next_table_id("level_progressions")
        self.client.table("level_progressions").insert({
            "id": next_progression_id,
            "user_id": self.user_id,
            "level": level,
            "unlocked_at": unlocked_at,
            "started_at": unlocked_at,
            "created_at": now,
            "updated_at": now,
        }).execute()

    async def _next_table_id(self, table_name: str) -> int:
        result = self.client.table(table_name).select("id").order("id", desc=True).limit(1).execute()
        if not result.data:
            return 1
        return int(result.data[0]["id"]) + 1

    async def _get_template_subjects(
        self,
        level: Optional[int] = None,
        ids: Optional[List[int]] = None,
    ) -> List[dict]:
        subject_rows: List[dict] = []
        for template_user_id in [None, SYSTEM_SUBJECT_USER_ID, LEGACY_TEMPLATE_USER_ID]:
            query = self.client.table("subjects").select("*").order("lesson_position").order("id")
            if template_user_id is None:
                query = query.is_("user_id", "null")
            else:
                query = query.eq("user_id", template_user_id)
            if level is not None:
                query = query.eq("level", level)
            if ids:
                query = query.in_("id", ids)
            result = query.execute()
            if result.data:
                subject_rows = result.data
                break

        if subject_rows:
            return subject_rows

        if level not in (None, 1):
            return []

        fallback_subjects = FALLBACK_SYSTEM_SUBJECTS
        if ids:
            fallback_subjects = [subject for subject in fallback_subjects if subject["id"] in ids]
        return fallback_subjects

    async def _get_template_subject(self, subject_id: int) -> Optional[dict]:
        subjects = await self._get_template_subjects(ids=[subject_id])
        return subjects[0] if subjects else None

    async def _get_any_subject(self, subject_id: int) -> Optional[dict]:
        subject = await self._get_template_subject(subject_id)
        if subject:
            return subject
        user_subject_res = self.client.table("subjects") \
            .select("*") \
            .eq("user_id", self.user_id) \
            .eq("id", int(subject_id)) \
            .limit(1) \
            .execute()
        return user_subject_res.data[0] if user_subject_res.data else None

    async def _get_existing_user_assignments(self) -> List[dict]:
        result = self.client.table("assignments").select("*").eq("user_id", self.user_id).order("id").execute()
        return result.data or []

    async def _sync_unlocked_assignments(self, user_data: dict, trigger_time: datetime) -> None:
        user_level = max(int(user_data.get("level") or 1), 1)
        assignments = await self._get_existing_user_assignments()
        assigned_subject_ids = {assignment["subject_id"] for assignment in assignments}
        passed_subject_ids = {
            assignment["subject_id"]
            for assignment in assignments
            if assignment.get("passed_at") or (assignment.get("srs_stage") or 0) >= 5
        }

        current_level_subjects = await self._get_template_subjects(level=user_level)
        unlockable_subjects = [
            subject
            for subject in current_level_subjects
            if subject["id"] not in assigned_subject_ids
            and self._subject_prereqs_satisfied(subject, passed_subject_ids)
        ]

        if unlockable_subjects:
            now_iso = trigger_time.isoformat()
            await self._ensure_assignments_for_subjects(unlockable_subjects, now_iso, now_iso)

    def _subject_prereqs_satisfied(self, subject: dict, passed_subject_ids: set[int]) -> bool:
        subject_type = subject["type"]
        component_ids = set(subject.get("component_subject_ids") or [])

        if subject_type in {"radical", "kana_vocabulary"} and not component_ids:
            return True
        if not component_ids:
            return True

        return component_ids.issubset(passed_subject_ids)

    async def _get_current_level_template_kanji(self, level: int) -> List[dict]:
        subjects = await self._get_template_subjects(level=level)
        return [subject for subject in subjects if subject["type"] == "kanji"]

    async def _maybe_advance_level(self, trigger_time: datetime) -> None:
        user_res = self.client.table("users").select("*").eq("id", self.user_id).limit(1).execute()
        if not user_res.data:
            return

        user_data = user_res.data[0]
        current_level = max(int(user_data.get("level") or 1), 1)
        current_level_kanji = await self._get_current_level_template_kanji(current_level)
        if not current_level_kanji:
            return

        kanji_ids = [subject["id"] for subject in current_level_kanji]
        assignment_res = self.client.table("assignments") \
            .select("subject_id, passed_at, srs_stage") \
            .eq("user_id", self.user_id) \
            .in_("subject_id", kanji_ids) \
            .execute()
        assignment_map = {row["subject_id"]: row for row in (assignment_res.data or [])}
        if len(assignment_map) < len(kanji_ids):
            return

        all_passed = all(
            assignment_map[subject_id].get("passed_at") or (assignment_map[subject_id].get("srs_stage") or 0) >= 5
            for subject_id in kanji_ids
        )
        if not all_passed:
            return

        next_level = current_level + 1
        next_level_subjects = await self._get_template_subjects(level=next_level)
        if not next_level_subjects:
            return

        now_iso = trigger_time.isoformat()
        self.client.table("users").update({
            "level": next_level,
            "updated_at": now_iso,
        }).eq("id", self.user_id).execute()

        current_progression = self.client.table("level_progressions") \
            .select("*") \
            .eq("user_id", self.user_id) \
            .eq("level", current_level) \
            .limit(1) \
            .execute()
        if current_progression.data:
            self.client.table("level_progressions").update({
                "passed_at": current_progression.data[0].get("passed_at") or now_iso,
                "completed_at": current_progression.data[0].get("completed_at") or now_iso,
                "updated_at": now_iso,
            }).eq("id", current_progression.data[0]["id"]).execute()

        await self._ensure_level_progression({"level": next_level}, now_iso, now_iso)
        await self._sync_unlocked_assignments({"level": next_level}, trigger_time)

    def format_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            # Ensure it is WaniKani compatible (ISO 8601 with Z)
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
        except:
            return date_str

    def format_collection(
        self,
        data: List[dict],
        object_name: str,
        path: str,
        *,
        total_count: Optional[int] = None,
        next_url: Optional[str] = None,
        previous_url: Optional[str] = None,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE
    ) -> dict:
        return {
            "object": "collection",
            "url": f"{self.base_url}{path}",
            "pages": {
                "next_url": next_url,
                "previous_url": previous_url,
                "per_page": per_page
            },
            "total_count": total_count if total_count is not None else len(data),
            "data_updated_at": datetime.utcnow().isoformat() + "Z",
            "data": data
        }

    # ─── Listing Methods (Querying Views) ───

    async def get_summary(self) -> dict:
        """Get summary report of available lessons and reviews."""
        await self.ensure_user_learning_state()
        now = datetime.utcnow()
        now_iso = self._format_date(now)

        lessons_res = self.client.table("assignments")\
            .select("subject_id")\
            .eq("user_id", self.user_id)\
            .filter("started_at", "is", "null")\
            .execute()
        
        # Reviews: available_at <= now
        reviews_res = self.client.table("assignments")\
            .select("subject_id, available_at")\
            .eq("user_id", self.user_id)\
            .not_.filter("started_at", "is", "null")\
            .lte("available_at", now.isoformat())\
            .execute()

        next_reviews_res = self.client.table("assignments")\
            .select("available_at")\
            .eq("user_id", self.user_id)\
            .not_.filter("available_at", "is", "null")\
            .gte("available_at", now.isoformat())\
            .order("available_at")\
            .limit(1)\
            .execute()
        
        lesson_subject_ids = [r["subject_id"] for r in (lessons_res.data or [])]
        review_subject_ids = [r["subject_id"] for r in (reviews_res.data or [])]
        next_reviews_at = None
        if next_reviews_res.data:
            next_reviews_at = self._format_date(next_reviews_res.data[0].get("available_at"))
        
        return {
            "object": "report",
            "url": f"{self.base_url}/summary",
            "data_updated_at": now_iso,
            "data": {
                "lessons": [{"available_at": now_iso, "subject_ids": lesson_subject_ids}],
                "reviews": [{"available_at": now_iso, "subject_ids": review_subject_ids}],
                "next_reviews_at": next_reviews_at
            }
        }

    async def get_subjects(
        self,
        updated_after: Optional[datetime] = None,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE
    ) -> dict:
        await self.ensure_user_learning_state()
        user_res = self.client.table("users").select("level").eq("id", self.user_id).limit(1).execute()
        user_level = max(int((user_res.data or [{"level": 1}])[0].get("level") or 1), 1)
        subject_rows = await self._get_template_subjects(level=user_level)
        assignment_res = self.client.table("assignments").select("subject_id").eq("user_id", self.user_id).execute()
        assigned_subject_ids = [row["subject_id"] for row in (assignment_res.data or [])]
        assigned_subject_rows = await self._get_template_subjects(ids=assigned_subject_ids) if assigned_subject_ids else []
        user_subject_rows = self.client.table("subjects") \
            .select("*") \
            .eq("user_id", self.user_id) \
            .order("lesson_position") \
            .order("id") \
            .execute()
        subject_map = {subject["id"]: subject for subject in subject_rows}
        for subject in assigned_subject_rows:
            subject_map[subject["id"]] = subject
        for subject in (user_subject_rows.data or []):
            subject_map[subject["id"]] = subject
        subject_rows = list(subject_map.values())
        subject_rows.sort(key=lambda subject: (subject.get("level", 0), subject.get("lesson_position", 0), subject["id"]))

        subject_rows = self._apply_updated_after_filter(subject_rows, updated_after)
        page_subject_rows, next_url, previous_url, total_count = self._paginate_rows(
            subject_rows,
            "/subjects",
            page_after=page_after,
            per_page=per_page,
            params={"updated_after": updated_after},
        )

        data = [self._format_object(item, item["type"], "/subjects") for item in page_subject_rows]
        return self.format_collection(
            data,
            "subject",
            "/subjects",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_subject(self, subject_id: WKID) -> dict:
        await self.ensure_user_learning_state()
        item = await self._get_template_subject(int(subject_id))
        if not item:
            user_subject_res = self.client.table("subjects").select("*").eq("user_id", self.user_id).eq("id", int(subject_id)).limit(1).execute()
            if not user_subject_res.data:
                raise ValueError("Subject not found")
            item = user_subject_res.data[0]
        return self._format_object(item, item["type"], "/subjects")

    async def get_assignments(
        self,
        updated_after: Optional[datetime] = None,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        **kwargs
    ) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("assignments").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        if kwargs.get("ids"):
            query = query.in_("id", kwargs["ids"])
        if kwargs.get("subject_ids"):
            query = query.in_("subject_id", kwargs["subject_ids"])
        if kwargs.get("subject_types"):
            query = query.in_("subject_type", kwargs["subject_types"])
        if kwargs.get("levels"):
            query = query.in_("level", kwargs["levels"])
        if kwargs.get("srs_stages"):
            query = query.in_("srs_stage", kwargs["srs_stages"])
        if kwargs.get("available_after"):
            query = query.gte("available_at", kwargs["available_after"].isoformat())
        if kwargs.get("available_before"):
            query = query.lte("available_at", kwargs["available_before"].isoformat())
        if kwargs.get("started") is True:
            query = query.not_.filter("started_at", "is", "null")
        elif kwargs.get("started") is False:
            query = query.filter("started_at", "is", "null")
        if kwargs.get("immediately_available_for_lessons") is True:
            query = query.filter("started_at", "is", "null")
        if kwargs.get("immediately_available_for_review") is True:
            query = query.not_.filter("started_at", "is", "null").lte("available_at", datetime.utcnow().isoformat())
        if kwargs.get("in_review") is True:
            query = query.not_.filter("started_at", "is", "null").filter("burned_at", "is", "null")
        elif kwargs.get("in_review") is False:
            query = query.filter("started_at", "is", "null")
        if kwargs.get("unlocked") is True:
            query = query.not_.filter("unlocked_at", "is", "null")
        elif kwargs.get("unlocked") is False:
            query = query.filter("unlocked_at", "is", "null")
        if kwargs.get("hidden") is not None:
            query = query.eq("hidden", kwargs["hidden"])
        if kwargs.get("burned") is True:
            query = query.not_.filter("burned_at", "is", "null")
        elif kwargs.get("burned") is False:
            query = query.filter("burned_at", "is", "null")

        result = query.execute()
        rows = result.data or []
        page_rows, next_url, previous_url, total_count = self._paginate_rows(
            rows,
            "/assignments",
            page_after=page_after,
            per_page=per_page,
            params={**kwargs, "updated_after": updated_after},
        )
        data = [self._format_object(item, "assignment", "/assignments") for item in page_rows]
        return self.format_collection(
            data,
            "assignment",
            "/assignments",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_assignment(self, assignment_id: WKID) -> dict:
        query = self.client.table("assignments").select("*").eq("user_id", self.user_id).eq("id", assignment_id)
        result = query.execute()
        if not result.data:
            # Fallback for subject_id as assignment_id
            result = self.client.table("assignments").select("*").eq("user_id", self.user_id).eq("subject_id", assignment_id).execute()
            if not result.data:
                raise ValueError("Assignment not found")
        
        return self._format_object(result.data[0], "assignment", "/assignments")

    async def get_review_statistics(
        self,
        updated_after: Optional[datetime] = None,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        **kwargs
    ) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("review_statistics").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        if kwargs.get("subject_types"):
            query = query.in_("subject_type", kwargs["subject_types"])
        if kwargs.get("hidden") is not None:
            query = query.eq("hidden", kwargs["hidden"])
        if kwargs.get("percentages_greater_than") is not None:
            query = query.gt("percentage_correct", kwargs["percentages_greater_than"])
        if kwargs.get("percentages_less_than") is not None:
            query = query.lt("percentage_correct", kwargs["percentages_less_than"])
        
        result = query.execute()
        rows = result.data or []
        rows = self._apply_ids_filter(rows, kwargs.get("ids"))
        rows = self._apply_field_ids_filter(rows, "subject_id", kwargs.get("subject_ids"))
        page_rows, next_url, previous_url, total_count = self._paginate_rows(
            rows,
            "/review_statistics",
            page_after=page_after,
            per_page=per_page,
            params={**kwargs, "updated_after": updated_after},
        )
        data = [self._format_object(item, "review_statistic", "/review_statistics") for item in page_rows]
        return self.format_collection(
            data,
            "review_statistic",
            "/review_statistics",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_review_statistic(self, statistic_id: WKID) -> dict:
        query = self.client.table("review_statistics").select("*").eq("user_id", self.user_id).eq("id", statistic_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Review statistic not found")
        return self._format_object(result.data[0], "review_statistic", "/review_statistics")

    async def get_level_progressions(
        self,
        updated_after: Optional[datetime] = None,
        ids: Optional[str] = None,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        **kwargs
    ) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("level_progressions").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        id_list = self._parse_csv_ids(ids)
        if id_list:
            query = query.in_("id", id_list)
            
        result = query.execute()
        rows = result.data or []
        page_rows, next_url, previous_url, total_count = self._paginate_rows(
            rows,
            "/level_progressions",
            page_after=page_after,
            per_page=per_page,
            params={"ids": ids, "updated_after": updated_after, **kwargs},
        )
        data = [self._format_object(item, "level_progression", "/level_progressions") for item in page_rows]
        return self.format_collection(
            data,
            "level_progression",
            "/level_progressions",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_level_progression(self, progression_id: WKID) -> dict:
        query = self.client.table("level_progressions").select("*").eq("user_id", self.user_id).eq("id", progression_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Level progression not found")
        return self._format_object(result.data[0], "level_progression", "/level_progressions")

    async def get_resets(
        self,
        updated_after: Optional[datetime] = None,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        **kwargs
    ) -> dict:
        query = self.client.table("resets").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        result = query.execute()
        rows = result.data or []
        page_rows, next_url, previous_url, total_count = self._paginate_rows(
            rows,
            "/resets",
            page_after=page_after,
            per_page=per_page,
            params={"updated_after": updated_after, **kwargs},
        )
        data = [self._format_object(item, "reset", "/resets") for item in page_rows]
        return self.format_collection(
            data,
            "reset",
            "/resets",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_reset(self, reset_id: WKID) -> dict:
        query = self.client.table("resets").select("*").eq("user_id", self.user_id).eq("id", reset_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Reset not found")
        return self._format_object(result.data[0], "reset", "/resets")

    async def get_reviews(
        self,
        updated_after: Optional[datetime] = None,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        **kwargs
    ) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("reviews").select("*").eq("user_id", self.user_id).order("created_at")
        if updated_after:
            query = query.gte("created_at", updated_after.isoformat())
            
        result = query.execute()
        rows = result.data or []
        rows = self._apply_ids_filter(rows, kwargs.get("ids"))
        rows = self._apply_field_ids_filter(rows, "assignment_id", kwargs.get("assignment_ids"))
        rows = self._apply_field_ids_filter(rows, "subject_id", kwargs.get("subject_ids"))
        page_rows, next_url, previous_url, total_count = self._paginate_rows(
            rows,
            "/reviews",
            page_after=page_after,
            per_page=per_page,
            params={**kwargs, "updated_after": updated_after},
        )
        data = [self._format_object(item, "review", "/reviews") for item in page_rows]
        return self.format_collection(
            data,
            "review",
            "/reviews",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_review(self, review_id: WKID) -> dict:
        query = self.client.table("reviews").select("*").eq("user_id", self.user_id).eq("id", review_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Review not found")
        return self._format_object(result.data[0], "review", "/reviews")

    async def get_spaced_repetition_systems(
        self,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        **kwargs
    ) -> dict:
        query = self.client.table("spaced_repetition_systems").select("*").order("id")
        parsed_ids = self._parse_csv_ids(kwargs.get("ids"))
        if parsed_ids:
            query = query.in_("id", parsed_ids)
        result = query.execute()
        rows = result.data or []
        page_rows, next_url, previous_url, total_count = self._paginate_rows(
            rows,
            "/spaced_repetition_systems",
            page_after=page_after,
            per_page=per_page,
            params=kwargs,
        )
        data = [self._format_object(item, "spaced_repetition_system", "/spaced_repetition_systems") for item in page_rows]
        return self.format_collection(
            data,
            "spaced_repetition_system",
            "/spaced_repetition_systems",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_spaced_repetition_system(self, srs_id: WKID) -> dict:
        query = self.client.table("spaced_repetition_systems").select("*").eq("id", srs_id)
        result = query.execute()
        if not result.data:
            raise ValueError("SRS not found")
        return self._format_object(result.data[0], "spaced_repetition_system", "/spaced_repetition_systems")

    async def get_study_materials(
        self,
        updated_after: Optional[datetime] = None,
        page_after: int = 0,
        per_page: int = DEFAULT_COLLECTION_PAGE_SIZE,
        **kwargs
    ) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("study_materials").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        result = query.execute()
        rows = self._apply_ids_filter(result.data or [], kwargs.get("ids"))
        page_rows, next_url, previous_url, total_count = self._paginate_rows(
            rows,
            "/study_materials",
            page_after=page_after,
            per_page=per_page,
            params={**kwargs, "updated_after": updated_after},
        )
        data = [self._format_object(item, "study_material", "/study_materials") for item in page_rows]
        return self.format_collection(
            data,
            "study_material",
            "/study_materials",
            total_count=total_count,
            next_url=next_url,
            previous_url=previous_url,
            per_page=min(max(int(per_page or DEFAULT_COLLECTION_PAGE_SIZE), 1), DEFAULT_COLLECTION_PAGE_SIZE),
        )

    async def get_study_material(self, material_id: WKID) -> dict:
        query = self.client.table("study_materials").select("*").eq("user_id", self.user_id).eq("id", material_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Study material not found")
        return self._format_object(result.data[0], "study_material", "/study_materials")

    async def create_study_material(self, subject_id: WKID, meaning_note: str = None, reading_note: str = None, meaning_synonyms: list = None) -> dict:
        await self.ensure_user_learning_state()
        subject = await self._get_any_subject(int(subject_id))
        if not subject:
            raise ValueError("Subject not found")
        now = datetime.utcnow().isoformat()
        next_id = await self._next_table_id("study_materials")
        data = {
            "id": next_id,
            "user_id": self.user_id,
            "subject_id": subject_id,
            "subject_type": subject["type"],
            "meaning_note": meaning_note,
            "reading_note": reading_note,
            "meaning_synonyms": meaning_synonyms or [],
            "hidden": False,
            "created_at": now,
            "updated_at": now
        }
        result = self.client.table("study_materials").insert(data).execute()
        if not result.data:
             raise ValueError("Failed to create study material")
        return self._format_object(result.data[0], "study_material", "/study_materials")

    async def update_study_material(self, material_id: WKID, meaning_note: str = None, reading_note: str = None, meaning_synonyms: list = None) -> dict:
        await self.ensure_user_learning_state()
        now = datetime.utcnow().isoformat()
        data = {"updated_at": now}
        if meaning_note is not None: data["meaning_note"] = meaning_note
        if reading_note is not None: data["reading_note"] = reading_note
        if meaning_synonyms is not None: data["meaning_synonyms"] = meaning_synonyms
        
        result = self.client.table("study_materials").update(data).eq("user_id", self.user_id).eq("id", material_id).execute()
        if not result.data:
            raise ValueError("Study material not found")
        return self._format_object(result.data[0], "study_material", "/study_materials")

    # ─── Mutation Methods (Writing to Base Tables) ───

    async def start_assignment(self, assignment_id: WKID, started_at: Optional[datetime] = None) -> dict:
        await self.ensure_user_learning_state()
        start_time = started_at or datetime.utcnow()
        lookup = self.client.table("assignments").select("*").eq("user_id", self.user_id).eq("id", int(assignment_id)).limit(1).execute()
        if not lookup.data:
            raise ValueError(f"Assignment not found: {assignment_id}")

        assignment = lookup.data[0]
        now = datetime.utcnow().isoformat()
        update_data = {
            "started_at": assignment.get("started_at") or start_time.isoformat(),
            "srs_stage": max(assignment.get("srs_stage") or 0, 1),
            "available_at": self.calculate_next_review_at(1, start_time).isoformat(),
            "updated_at": now
        }

        self.client.table("assignments").update(update_data).eq("user_id", self.user_id).eq("id", assignment["id"]).execute()
        return await self.get_assignment(assignment["id"])

    async def create_review(
        self,
        assignment_id: WKID,
        incorrect_meaning_answers: int,
        incorrect_reading_answers: int,
        created_at: Optional[datetime] = None
    ) -> dict:
        await self.ensure_user_learning_state()
        review_time = created_at or datetime.utcnow()

        result = self.client.table("assignments").select("*").eq("user_id", self.user_id).eq("id", int(assignment_id)).limit(1).execute()
        if not result.data:
            raise ValueError(f"Assignment not found: {assignment_id}")

        state = result.data[0]
        starting_stage = max(state.get("srs_stage", 0), 1)
        total_incorrect = incorrect_meaning_answers + incorrect_reading_answers
        new_stage = self.calculate_new_srs_stage(starting_stage, total_incorrect)
        next_review_at = self.calculate_next_review_at(new_stage, review_time)

        review_data = {
            "id": await self._next_table_id("reviews"),
            "user_id": self.user_id,
            "subject_id": state["subject_id"],
            "assignment_id": state["id"],
            "spaced_repetition_system_id": DEFAULT_SRS_ID,
            "starting_srs_stage": starting_stage,
            "ending_srs_stage": new_stage,
            "incorrect_meaning_answers": incorrect_meaning_answers,
            "incorrect_reading_answers": incorrect_reading_answers,
            "created_at": review_time.isoformat(),
            "updated_at": review_time.isoformat(),
        }
        log_res = self.client.table("reviews").insert(review_data).execute()
        if not log_res.data:
            raise ValueError("Failed to log review")

        update_state = {
            "srs_stage": new_stage,
            "available_at": next_review_at.isoformat() if next_review_at else None,
            "started_at": state.get("started_at") or review_time.isoformat(),
            "passed_at": review_time.isoformat() if new_stage >= 5 and not state.get("passed_at") else state.get("passed_at"),
            "burned_at": review_time.isoformat() if new_stage == 9 else state.get("burned_at"),
            "updated_at": datetime.utcnow().isoformat()
        }
        self.client.table("assignments").update(update_state).eq("id", state["id"]).execute()

        if starting_stage < 5 and new_stage >= 5:
            await self._on_item_gurud(state, review_time)
        
        formatted_review_statistic = await self._update_review_stats(state, {
            "starting_srs_stage": starting_stage,
            "ending_srs_stage": new_stage,
            "incorrect_meaning_answers": incorrect_meaning_answers,
            "incorrect_reading_answers": incorrect_reading_answers
        })
        
        review_obj = log_res.data[0]
        formatted_assignment = await self.get_assignment(state["id"])
        
        return {
            "id": review_obj["id"],
            "object": "review",
            "url": f"{self.base_url}/reviews/{review_obj['id']}",
            "data_updated_at": self._format_date(review_time),
            "data": {
                "created_at": self._format_date(review_time),
                "assignment_id": state["id"],
                "subject_id": state["subject_id"],
                "starting_srs_stage": starting_stage,
                "ending_srs_stage": new_stage,
                "incorrect_meaning_answers": incorrect_meaning_answers,
                "incorrect_reading_answers": incorrect_reading_answers,
                "spaced_repetition_system_id": DEFAULT_SRS_ID
            },
            "resources_updated": {
                "assignment": formatted_assignment,
                "review_statistic": formatted_review_statistic,
            }
        }

    # ─── Logic & Helpers ───

    def _format_date(self, dt: Union[datetime, str]) -> str:
        """Ensure date is ISO 8601 with Z suffix (UTC)."""
        if dt is None: return None
        if isinstance(dt, str):
            dt = dt.replace("+00:00", "Z")
            if dt.endswith("Z"): return dt
            return dt + "Z"
        return dt.strftime('%Y-%m-%dT%H:%M:%S.000000Z')

    async def _update_review_stats(self, state: dict, ri: dict):
        """Update user review statistics after a review."""
        res = self.client.table("review_statistics")\
            .select("*")\
            .eq("user_id", self.user_id)\
            .eq("subject_id", state["subject_id"])\
            .execute()
            
        stats = res.data[0] if res.data else None
        
        m_inc = ri["incorrect_meaning_answers"]
        r_inc = ri["incorrect_reading_answers"]
        
        m_cor = 1 if m_inc == 0 else 0
        r_cor = 1 if r_inc == 0 else 0
        now = datetime.utcnow().isoformat()
        
        if stats:
            meaning_correct = stats["meaning_correct"] + m_cor
            meaning_incorrect = stats["meaning_incorrect"] + m_inc
            reading_correct = stats["reading_correct"] + r_cor
            reading_incorrect = stats["reading_incorrect"] + r_inc
            meaning_current_streak = stats["meaning_current_streak"] + 1 if m_inc == 0 else 0
            reading_current_streak = stats["reading_current_streak"] + 1 if r_inc == 0 else 0
            update_data = {
                "meaning_correct": meaning_correct,
                "meaning_incorrect": meaning_incorrect,
                "meaning_current_streak": meaning_current_streak,
                "meaning_max_streak": max(stats["meaning_max_streak"], meaning_current_streak),
                "reading_correct": reading_correct,
                "reading_incorrect": reading_incorrect,
                "reading_current_streak": reading_current_streak,
                "reading_max_streak": max(stats["reading_max_streak"], reading_current_streak),
                "percentage_correct": self._calculate_percentage_correct(
                    meaning_correct,
                    meaning_incorrect,
                    reading_correct,
                    reading_incorrect,
                ),
                "updated_at": now,
            }
            self.client.table("review_statistics").update(update_data).eq("id", stats["id"]).execute()
            return await self.get_review_statistic(stats["id"])
        else:
            insert_data = {
                "id": await self._next_table_id("review_statistics"),
                "user_id": self.user_id,
                "subject_id": state["subject_id"],
                "subject_type": state["subject_type"],
                "meaning_correct": m_cor,
                "meaning_incorrect": m_inc,
                "meaning_current_streak": 1 if m_inc == 0 else 0,
                "meaning_max_streak": 1 if m_inc == 0 else 0,
                "reading_correct": r_cor,
                "reading_incorrect": r_inc,
                "reading_current_streak": 1 if r_inc == 0 else 0,
                "reading_max_streak": 1 if r_inc == 0 else 0,
                "percentage_correct": self._calculate_percentage_correct(m_cor, m_inc, r_cor, r_inc),
                "hidden": False,
                "created_at": now,
                "updated_at": now,
            }
            result = self.client.table("review_statistics").insert(insert_data).execute()
            if result.data:
                return await self.get_review_statistic(result.data[0]["id"])
            return None

    def _calculate_percentage_correct(
        self,
        meaning_correct: int,
        meaning_incorrect: int,
        reading_correct: int,
        reading_incorrect: int,
    ) -> float:
        total = meaning_correct + meaning_incorrect + reading_correct + reading_incorrect
        if total == 0:
            return 0.0
        return round(((meaning_correct + reading_correct) / total) * 100, 1)

    def calculate_new_srs_stage(self, current: int, total_incorrect: int) -> int:
        if current == 0: return 1
        if total_incorrect == 0: return min(current + 1, 9)
        penalty = 1 if current < 5 else 2
        return max(1, current - penalty)

    def calculate_next_review_at(self, srs_stage: int, baseline: datetime) -> Optional[datetime]:
        if srs_stage >= 9: return None
        intervals = {
            1: timedelta(hours=4), 2: timedelta(hours=8), 3: timedelta(hours=23),
            4: timedelta(hours=47), 5: timedelta(days=7), 6: timedelta(days=14),
            7: timedelta(days=30), 8: timedelta(days=120)
        }
        return baseline + intervals.get(srs_stage, timedelta(hours=4))

    async def _on_item_gurud(self, state: dict, trigger_time: datetime):
        user_res = self.client.table("users").select("*").eq("id", self.user_id).limit(1).execute()
        if user_res.data:
            await self._sync_unlocked_assignments(user_res.data[0], trigger_time)
        await self._maybe_advance_level(trigger_time)
        user_res = self.client.table("users").select("*").eq("id", self.user_id).limit(1).execute()
        if user_res.data:
            await self._sync_unlocked_assignments(user_res.data[0], trigger_time)

    async def preflight_wanikani_sync(self, api_key: str) -> dict:
        await self.get_user()

        wanikani_base = settings.WANIKANI_API_URL
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Wanikani-Revision": "20170710",
        }

        async with httpx.AsyncClient(timeout=20.0) as http:
            try:
                user_resp = await http.get(f"{wanikani_base}/user", headers=headers)
                user_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = "Could not validate the WaniKani API key"
                if exc.response.status_code == 401:
                    detail = "Invalid WaniKani API key"
                raise ValueError(detail) from exc

        remote_user = user_resp.json().get("data", {})

        local_user_res = self.client.table("users").select("*").eq("id", self.user_id).limit(1).execute()
        local_user = (local_user_res.data or [{}])[0]

        assignments_count = len(
            self.client.table("assignments")
            .select("id")
            .eq("user_id", self.user_id)
            .execute()
            .data
            or []
        )
        review_statistics_count = len(
            self.client.table("review_statistics")
            .select("id")
            .eq("user_id", self.user_id)
            .execute()
            .data
            or []
        )
        level_progressions_count = len(
            self.client.table("level_progressions")
            .select("id")
            .eq("user_id", self.user_id)
            .execute()
            .data
            or []
        )
        reviews_count = len(
            self.client.table("reviews")
            .select("id")
            .eq("user_id", self.user_id)
            .execute()
            .data
            or []
        )

        warnings: List[str] = []
        local_username = (local_user.get("username") or "").strip()
        remote_username = (remote_user.get("username") or "").strip()
        local_level = local_user.get("level") or 1
        remote_level = remote_user.get("level") or 1
        has_existing_progress = any([
            assignments_count,
            review_statistics_count,
            level_progressions_count,
            reviews_count,
        ])

        if local_username and remote_username and local_username.lower() != remote_username.lower():
            warnings.append(
                f"Current account username '{local_username}' does not match WaniKani username '{remote_username}'."
            )
        if local_level != remote_level:
            warnings.append(
                f"Current account level is {local_level}, but WaniKani reports level {remote_level}."
            )
        if has_existing_progress:
            warnings.append(
                "This account already has study progress. Merge keeps existing progress; replace discards it before importing."
            )

        return {
            "remote_user": {
                "username": remote_username,
                "level": remote_level,
                "profile_url": remote_user.get("profile_url"),
                "started_at": remote_user.get("started_at"),
                "subscription": remote_user.get("subscription") or {},
            },
            "local_user": {
                "id": str(local_user.get("id") or self.user_id),
                "username": local_username or "User",
                "level": local_level,
            },
            "server_data_counts": {
                "assignments": assignments_count,
                "review_statistics": review_statistics_count,
                "level_progressions": level_progressions_count,
                "reviews": reviews_count,
            },
            "has_existing_progress": has_existing_progress,
            "recommended_mode": "merge" if has_existing_progress else "overwrite",
            "warnings": warnings,
        }

    async def _fetch_wanikani_pages(
        self,
        http: httpx.AsyncClient,
        url: str,
        headers: dict
    ) -> List[dict]:
        items: List[dict] = []
        next_url: Optional[str] = url

        while next_url:
            response = await http.get(next_url, headers=headers)
            response.raise_for_status()
            payload = response.json()
            items.extend(payload.get("data", []))
            next_url = payload.get("pages", {}).get("next_url")

        return items

    def _chunked(self, items: List[dict], chunk_size: int) -> List[List[dict]]:
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    async def _upsert_subject_rows(self, subject_rows: List[dict]) -> None:
        if not subject_rows:
            return

        for chunk in self._chunked(subject_rows, 25):
            self.client.table("subjects").upsert(chunk, on_conflict="id").execute()

    async def _upsert_assignment_rows(self, assignment_rows: List[dict]) -> int:
        if not assignment_rows:
            return 0

        existing_rows = self.client.table("assignments") \
            .select("id, subject_id") \
            .eq("user_id", self.user_id) \
            .execute()
        existing_by_subject = {
            int(row["subject_id"]): int(row["id"])
            for row in (existing_rows.data or [])
        }
        next_id = await self._next_table_id("assignments")
        imported = 0

        for row in assignment_rows:
            subject_id = int(row["subject_id"])
            if subject_id in existing_by_subject:
                self.client.table("assignments") \
                    .update(row) \
                    .eq("id", existing_by_subject[subject_id]) \
                    .execute()
            else:
                row["id"] = next_id
                next_id += 1
                self.client.table("assignments").insert(row).execute()
            imported += 1

        return imported

    async def _upsert_review_statistic_rows(self, statistic_rows: List[dict]) -> int:
        if not statistic_rows:
            return 0

        existing_rows = self.client.table("review_statistics") \
            .select("id, subject_id") \
            .eq("user_id", self.user_id) \
            .execute()
        existing_by_subject = {
            int(row["subject_id"]): int(row["id"])
            for row in (existing_rows.data or [])
        }
        next_id = await self._next_table_id("review_statistics")
        imported = 0

        for row in statistic_rows:
            subject_id = int(row["subject_id"])
            if subject_id in existing_by_subject:
                self.client.table("review_statistics") \
                    .update(row) \
                    .eq("id", existing_by_subject[subject_id]) \
                    .execute()
            else:
                row["id"] = next_id
                next_id += 1
                self.client.table("review_statistics").insert(row).execute()
            imported += 1

        return imported

    async def _upsert_study_material_rows(self, material_rows: List[dict]) -> int:
        if not material_rows:
            return 0

        existing_rows = self.client.table("study_materials") \
            .select("id, subject_id") \
            .eq("user_id", self.user_id) \
            .execute()
        existing_by_subject = {
            int(row["subject_id"]): int(row["id"])
            for row in (existing_rows.data or [])
        }
        next_id = await self._next_table_id("study_materials")
        imported = 0

        for row in material_rows:
            subject_id = int(row["subject_id"])
            if subject_id in existing_by_subject:
                self.client.table("study_materials") \
                    .update(row) \
                    .eq("id", existing_by_subject[subject_id]) \
                    .execute()
            else:
                row["id"] = next_id
                next_id += 1
                self.client.table("study_materials").insert(row).execute()
            imported += 1

        return imported

    async def _upsert_level_progression_rows(self, progression_rows: List[dict]) -> int:
        if not progression_rows:
            return 0

        existing_rows = self.client.table("level_progressions") \
            .select("id, level") \
            .eq("user_id", self.user_id) \
            .execute()
        existing_by_level = {
            int(row["level"]): int(row["id"])
            for row in (existing_rows.data or [])
        }
        next_id = await self._next_table_id("level_progressions")
        imported = 0

        for row in progression_rows:
            level = int(row["level"])
            if level in existing_by_level:
                self.client.table("level_progressions") \
                    .update(row) \
                    .eq("id", existing_by_level[level]) \
                    .execute()
            else:
                row["id"] = next_id
                next_id += 1
                self.client.table("level_progressions").insert(row).execute()
            imported += 1

        return imported

    async def _upsert_review_rows(self, review_rows: List[dict]) -> int:
        if not review_rows:
            return 0

        existing_rows = self.client.table("reviews") \
            .select("id, assignment_id, created_at, starting_srs_stage, ending_srs_stage, incorrect_meaning_answers, incorrect_reading_answers") \
            .eq("user_id", self.user_id) \
            .execute()
        existing_keys = {
            (
                int(row["assignment_id"]),
                row.get("created_at"),
                int(row.get("starting_srs_stage") or 0),
                int(row.get("ending_srs_stage") or 0),
                int(row.get("incorrect_meaning_answers") or 0),
                int(row.get("incorrect_reading_answers") or 0),
            )
            for row in (existing_rows.data or [])
        }
        next_id = await self._next_table_id("reviews")
        imported = 0

        for row in review_rows:
            review_key = (
                int(row["assignment_id"]),
                row.get("created_at"),
                int(row.get("starting_srs_stage") or 0),
                int(row.get("ending_srs_stage") or 0),
                int(row.get("incorrect_meaning_answers") or 0),
                int(row.get("incorrect_reading_answers") or 0),
            )
            if review_key in existing_keys:
                continue
            row["id"] = next_id
            next_id += 1
            self.client.table("reviews").insert(row).execute()
            existing_keys.add(review_key)
            imported += 1

        return imported

    async def sync_wanikani(self, api_key: str, mode: str = "merge") -> dict:
        """
        Sync subjects, assignments, and review_statistics from WaniKani API.
        Replaces the crawl-wanikani Edge Function.
        """
        await self.get_user()

        if mode == "overwrite":
            self.client.table("assignments").delete().eq("user_id", self.user_id).execute()
            self.client.table("review_statistics").delete().eq("user_id", self.user_id).execute()
            self.client.table("reviews").delete().eq("user_id", self.user_id).execute()
            self.client.table("level_progressions").delete().eq("user_id", self.user_id).execute()
            self.client.table("study_materials").delete().eq("user_id", self.user_id).execute()

        wanikani_base = settings.WANIKANI_API_URL
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Wanikani-Revision": "20170710",
        }

        async with httpx.AsyncClient(timeout=60.0) as http:
            wk_user_payload = await http.get(f"{wanikani_base}/user", headers=headers)
            wk_user_payload.raise_for_status()
            wk_user = wk_user_payload.json().get("data", {})

            wk_subjects = await self._fetch_wanikani_pages(http, f"{wanikani_base}/subjects", headers)
            wk_assignments = await self._fetch_wanikani_pages(http, f"{wanikani_base}/assignments", headers)
            wk_review_statistics = await self._fetch_wanikani_pages(http, f"{wanikani_base}/review_statistics", headers)
            wk_reviews = await self._fetch_wanikani_pages(http, f"{wanikani_base}/reviews", headers)
            wk_study_materials = await self._fetch_wanikani_pages(http, f"{wanikani_base}/study_materials", headers)
            wk_level_progressions = await self._fetch_wanikani_pages(http, f"{wanikani_base}/level_progressions", headers)

        subject_rows = []
        for item in wk_subjects:
            data = item.get("data", {})
            timestamp = data.get("created_at") or item.get("data_updated_at") or datetime.utcnow().isoformat()
            subject_rows.append({
                "id": int(item["id"]),
                "user_id": None,
                "type": item["object"],
                "slug": data.get("slug"),
                "level": data.get("level") or 1,
                "meaning_mnemonic": data.get("meaning_mnemonic"),
                "reading_mnemonic": data.get("reading_mnemonic"),
                "meaning_hint": data.get("meaning_hint"),
                "reading_hint": data.get("reading_hint"),
                "characters": data.get("characters"),
                "meanings": data.get("meanings") or [],
                "readings": data.get("readings") or [],
                "auxiliary_meanings": data.get("auxiliary_meanings") or [],
                "component_subject_ids": data.get("component_subject_ids") or [],
                "amalgamation_subject_ids": data.get("amalgamation_subject_ids") or [],
                "visually_similar_subject_ids": data.get("visually_similar_subject_ids") or [],
                "context_sentences": data.get("context_sentences") or [],
                "pronunciation_audios": data.get("pronunciation_audios") or [],
                "character_images": data.get("character_images") or [],
                "parts_of_speech": data.get("parts_of_speech") or [],
                "document_url": data.get("document_url"),
                "spaced_repetition_system_id": data.get("spaced_repetition_system_id") or DEFAULT_SRS_ID,
                "lesson_position": data.get("lesson_position") or 0,
                "hidden_at": data.get("hidden_at"),
                "created_at": timestamp,
                "updated_at": item.get("data_updated_at") or timestamp,
            })
        await self._upsert_subject_rows(subject_rows)
        subject_map = {
            int(subject["id"]): subject
            for subject in subject_rows
        }

        assignment_rows = []
        for item in wk_assignments:
            data = item.get("data", {})
            subject_id = data.get("subject_id")
            if subject_id is None:
                continue
            subject = subject_map.get(int(subject_id), {})
            assignment_rows.append({
                "user_id": self.user_id,
                "subject_id": int(subject_id),
                "subject_type": subject.get("type") or data.get("subject_type") or "radical",
                "level": subject.get("level") or data.get("level") or 1,
                "srs_stage": data.get("srs_stage") or 0,
                "unlocked_at": data.get("unlocked_at"),
                "started_at": data.get("started_at"),
                "passed_at": data.get("passed_at"),
                "burned_at": data.get("burned_at"),
                "available_at": data.get("available_at"),
                "resurrected_at": data.get("resurrected_at"),
                "hidden": data.get("hidden") or False,
                "created_at": data.get("created_at") or item.get("data_updated_at") or datetime.utcnow().isoformat(),
                "updated_at": item.get("data_updated_at") or data.get("created_at") or datetime.utcnow().isoformat(),
            })
        total_assignments = await self._upsert_assignment_rows(assignment_rows)

        statistic_rows = []
        for item in wk_review_statistics:
            data = item.get("data", {})
            subject_id = data.get("subject_id")
            if subject_id is None:
                continue
            subject = subject_map.get(int(subject_id), {})
            statistic_rows.append({
                "user_id": self.user_id,
                "subject_id": int(subject_id),
                "subject_type": subject.get("type") or data.get("subject_type") or "radical",
                "meaning_correct": data.get("meaning_correct") or 0,
                "meaning_incorrect": data.get("meaning_incorrect") or 0,
                "meaning_current_streak": data.get("meaning_current_streak") or 0,
                "meaning_max_streak": data.get("meaning_max_streak") or 0,
                "reading_correct": data.get("reading_correct") or 0,
                "reading_incorrect": data.get("reading_incorrect") or 0,
                "reading_current_streak": data.get("reading_current_streak") or 0,
                "reading_max_streak": data.get("reading_max_streak") or 0,
                "percentage_correct": data.get("percentage_correct") or 0,
                "hidden": data.get("hidden") or False,
                "created_at": data.get("created_at") or item.get("data_updated_at") or datetime.utcnow().isoformat(),
                "updated_at": item.get("data_updated_at") or data.get("created_at") or datetime.utcnow().isoformat(),
            })
        total_stats = await self._upsert_review_statistic_rows(statistic_rows)

        material_rows = []
        for item in wk_study_materials:
            data = item.get("data", {})
            subject_id = data.get("subject_id")
            if subject_id is None:
                continue
            subject = subject_map.get(int(subject_id), {})
            material_rows.append({
                "user_id": self.user_id,
                "subject_id": int(subject_id),
                "subject_type": subject.get("type") or data.get("subject_type") or "radical",
                "meaning_note": data.get("meaning_note"),
                "reading_note": data.get("reading_note"),
                "meaning_synonyms": data.get("meaning_synonyms") or [],
                "hidden": data.get("hidden") or False,
                "created_at": data.get("created_at") or item.get("data_updated_at") or datetime.utcnow().isoformat(),
                "updated_at": item.get("data_updated_at") or data.get("created_at") or datetime.utcnow().isoformat(),
            })
        total_study_materials = await self._upsert_study_material_rows(material_rows)

        progression_rows = []
        for item in wk_level_progressions:
            data = item.get("data", {})
            progression_rows.append({
                "user_id": self.user_id,
                "level": data.get("level") or 1,
                "unlocked_at": data.get("unlocked_at"),
                "started_at": data.get("started_at"),
                "passed_at": data.get("passed_at"),
                "completed_at": data.get("completed_at"),
                "abandoned_at": data.get("abandoned_at"),
                "created_at": data.get("created_at") or item.get("data_updated_at") or datetime.utcnow().isoformat(),
                "updated_at": item.get("data_updated_at") or data.get("created_at") or datetime.utcnow().isoformat(),
            })
        total_level_progressions = await self._upsert_level_progression_rows(progression_rows)

        local_assignments = self.client.table("assignments") \
            .select("id, subject_id") \
            .eq("user_id", self.user_id) \
            .execute()
        assignment_id_by_subject = {
            int(row["subject_id"]): int(row["id"])
            for row in (local_assignments.data or [])
        }
        review_rows = []
        for item in wk_reviews:
            data = item.get("data", {})
            subject_id = data.get("subject_id")
            assignment_id = assignment_id_by_subject.get(int(subject_id or 0))
            if not assignment_id:
                continue
            review_rows.append({
                "user_id": self.user_id,
                "assignment_id": assignment_id,
                "subject_id": int(subject_id),
                "spaced_repetition_system_id": data.get("spaced_repetition_system_id") or DEFAULT_SRS_ID,
                "starting_srs_stage": data.get("starting_srs_stage") or 0,
                "ending_srs_stage": data.get("ending_srs_stage") or 0,
                "incorrect_meaning_answers": data.get("incorrect_meaning_answers") or 0,
                "incorrect_reading_answers": data.get("incorrect_reading_answers") or 0,
                "created_at": data.get("created_at") or item.get("data_updated_at") or datetime.utcnow().isoformat(),
                "updated_at": item.get("data_updated_at") or data.get("created_at") or datetime.utcnow().isoformat(),
            })
        total_reviews = await self._upsert_review_rows(review_rows)

        subscription = wk_user.get("subscription") or {}
        self.client.table("users").update({
            "username": wk_user.get("username"),
            "level": wk_user.get("level") or 1,
            "max_level_granted": subscription.get("max_level_granted") or 60,
            "subscription_type": subscription.get("type") or "free",
            "subscription_ends_at": subscription.get("period_ends_at"),
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", self.user_id).execute()

        return {
            "success": True,
            "mode": mode,
            "subjects_synced": len(subject_rows),
            "assignments_synced": total_assignments,
            "review_statistics_synced": total_stats,
            "reviews_synced": total_reviews,
            "study_materials_synced": total_study_materials,
            "level_progressions_synced": total_level_progressions,
        }
