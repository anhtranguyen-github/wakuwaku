import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

WKID = Union[int, str]
SYSTEM_SUBJECT_USER_ID = "00000000-0000-0000-0000-000000000000"
LEGACY_TEMPLATE_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_SRS_ID = 1

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
        
        # Determine the inner data
        if "data" in data and isinstance(data["data"], dict):
            inner = data["data"]
        else:
            # Filter out top-level resource fields from inner data
            inner = data.copy()
            for key in ["id", "object", "url", "data_updated_at", "updated_at", "type", "ku_id"]:
                if key in inner:
                    del inner[key]

        return {
            "id": obj_id, # Keep as native type (int if possible) for frontend compatibility
            "object": object_type,
            "url": f"{self.base_url}{url_prefix}/{str_id}",
            "data_updated_at": self._format_date(data.get("data_updated_at") or data.get("updated_at") or datetime.utcnow()),
            "data": inner
        }

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
                "profile_url": f"{self.base_url}/user",
                "started_at": self._format_date(user_data.get("created_at") or user_data.get("started_at")),
                "subscription": {
                    "active": True,
                    "max_level_granted": 60,
                    "period_ends_at": None,
                    "type": "recurring" # Hardcoded for now to avoid frontend limits
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
        for template_user_id in [SYSTEM_SUBJECT_USER_ID, LEGACY_TEMPLATE_USER_ID]:
            query = self.client.table("subjects").select("*").eq("user_id", template_user_id).order("lesson_position").order("id")
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

    def format_collection(self, data: List[dict], object_name: str, path: str) -> dict:
        return {
            "object": "collection",
            "url": f"{self.base_url}{path}",
            "pages": {
                "next_url": None,
                "previous_url": None,
                "per_page": 500
            },
            "total_count": len(data),
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
            .select("subject_id")\
            .eq("user_id", self.user_id)\
            .not_.filter("started_at", "is", "null")\
            .lte("available_at", now.isoformat())\
            .execute()
        
        lesson_subject_ids = [r["subject_id"] for r in (lessons_res.data or [])]
        review_subject_ids = [r["subject_id"] for r in (reviews_res.data or [])]
        
        return {
            "object": "report",
            "url": f"{self.base_url}/summary",
            "data_updated_at": now_iso,
            "data": {
                "lessons": [{"available_at": now_iso, "subject_ids": lesson_subject_ids}],
                "reviews": [{"available_at": now_iso, "subject_ids": review_subject_ids}],
                "next_reviews_at": now_iso # Simplification for now
            }
        }

    async def get_subjects(self, updated_after: Optional[datetime] = None) -> dict:
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

        if updated_after:
            updated_after_iso = updated_after.isoformat()
            subject_rows = [
                subject for subject in subject_rows
                if (subject.get("updated_at") or subject.get("created_at") or "") >= updated_after_iso
            ]

        data = [self._format_object(item, item["type"], "/subjects") for item in subject_rows]
        return self.format_collection(data, "subject", "/subjects")

    async def get_subject(self, subject_id: WKID) -> dict:
        await self.ensure_user_learning_state()
        item = await self._get_template_subject(int(subject_id))
        if not item:
            user_subject_res = self.client.table("subjects").select("*").eq("user_id", self.user_id).eq("id", int(subject_id)).limit(1).execute()
            if not user_subject_res.data:
                raise ValueError("Subject not found")
            item = user_subject_res.data[0]
        return self._format_object(item, item["type"], "/subjects")

    async def get_assignments(self, updated_after: Optional[datetime] = None, **kwargs) -> dict:
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
        if kwargs.get("started") is True:
            query = query.not_.filter("started_at", "is", "null")
        elif kwargs.get("started") is False:
            query = query.filter("started_at", "is", "null")
        if kwargs.get("immediately_available_for_lessons") is True:
            query = query.filter("started_at", "is", "null")
        if kwargs.get("immediately_available_for_review") is True:
            query = query.not_.filter("started_at", "is", "null").lte("available_at", datetime.utcnow().isoformat())
        if kwargs.get("hidden") is not None:
            query = query.eq("hidden", kwargs["hidden"])
        if kwargs.get("burned") is True:
            query = query.not_.filter("burned_at", "is", "null")
        elif kwargs.get("burned") is False:
            query = query.filter("burned_at", "is", "null")
        
        result = query.limit(500).execute()
        data = [self._format_object(item, "assignment", "/assignments") for item in result.data]
        return self.format_collection(data, "assignment", "/assignments")

    async def get_assignment(self, assignment_id: WKID) -> dict:
        query = self.client.table("assignments").select("*").eq("user_id", self.user_id).eq("id", assignment_id)
        result = query.execute()
        if not result.data:
            # Fallback for subject_id as assignment_id
            result = self.client.table("assignments").select("*").eq("user_id", self.user_id).eq("subject_id", assignment_id).execute()
            if not result.data:
                raise ValueError("Assignment not found")
        
        return self._format_object(result.data[0], "assignment", "/assignments")

    async def get_review_statistics(self, updated_after: Optional[datetime] = None, **kwargs) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("review_statistics").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        
        result = query.limit(500).execute()
        data = [self._format_object(item, "review_statistic", "/review_statistics") for item in result.data]
        return self.format_collection(data, "review_statistic", "/review_statistics")

    async def get_review_statistic(self, statistic_id: WKID) -> dict:
        query = self.client.table("review_statistics").select("*").eq("user_id", self.user_id).eq("id", statistic_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Review statistic not found")
        return self._format_object(result.data[0], "review_statistic", "/review_statistics")

    async def get_level_progressions(self, updated_after: Optional[datetime] = None, ids: Optional[str] = None, **kwargs) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("level_progressions").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        if ids:
            id_list = [i.strip() for i in ids.split(",") if i.strip()]
            if id_list:
                query = query.in_("id", id_list)
            
        result = query.limit(500).execute()
        data = [self._format_object(item, "level_progression", "/level_progressions") for item in result.data]
        return self.format_collection(data, "level_progression", "/level_progressions")

    async def get_level_progression(self, progression_id: WKID) -> dict:
        query = self.client.table("level_progressions").select("*").eq("user_id", self.user_id).eq("id", progression_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Level progression not found")
        return self._format_object(result.data[0], "level_progression", "/level_progressions")

    async def get_resets(self, updated_after: Optional[datetime] = None, **kwargs) -> dict:
        query = self.client.table("resets").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        result = query.execute()
        data = [self._format_object(item, "reset", "/resets") for item in (result.data or [])]
        return self.format_collection(data, "reset", "/resets")

    async def get_reset(self, reset_id: WKID) -> dict:
        query = self.client.table("resets").select("*").eq("user_id", self.user_id).eq("id", reset_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Reset not found")
        return self._format_object(result.data[0], "reset", "/resets")

    async def get_reviews(self, updated_after: Optional[datetime] = None, **kwargs) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("reviews").select("*").eq("user_id", self.user_id).order("created_at")
        if updated_after:
            query = query.gte("created_at", updated_after.isoformat())
            
        result = query.limit(500).execute()
        data = [self._format_object(item, "review", "/reviews") for item in (result.data or [])]
        return self.format_collection(data, "review", "/reviews")

    async def get_review(self, review_id: WKID) -> dict:
        query = self.client.table("reviews").select("*").eq("user_id", self.user_id).eq("id", review_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Review not found")
        return self._format_object(result.data[0], "review", "/reviews")

    async def get_spaced_repetition_systems(self, **kwargs) -> dict:
        query = self.client.table("spaced_repetition_systems").select("*").order("id")
        result = query.execute()
        data = [self._format_object(item, "spaced_repetition_system", "/spaced_repetition_systems") for item in (result.data or [])]
        return self.format_collection(data, "spaced_repetition_system", "/spaced_repetition_systems")

    async def get_spaced_repetition_system(self, srs_id: WKID) -> dict:
        query = self.client.table("spaced_repetition_systems").select("*").eq("id", srs_id)
        result = query.execute()
        if not result.data:
            raise ValueError("SRS not found")
        return self._format_object(result.data[0], "spaced_repetition_system", "/spaced_repetition_systems")

    async def get_study_materials(self, updated_after: Optional[datetime] = None, **kwargs) -> dict:
        await self.ensure_user_learning_state()
        query = self.client.table("study_materials").select("*").eq("user_id", self.user_id).order("id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        result = query.execute()
        data = [self._format_object(item, "study_material", "/study_materials") for item in (result.data or [])]
        return self.format_collection(data, "study_material", "/study_materials")

    async def get_study_material(self, material_id: WKID) -> dict:
        query = self.client.table("study_materials").select("*").eq("user_id", self.user_id).eq("id", material_id)
        result = query.execute()
        if not result.data:
            raise ValueError("Study material not found")
        return self._format_object(result.data[0], "study_material", "/study_materials")

    async def create_study_material(self, subject_id: WKID, meaning_note: str = None, reading_note: str = None, meaning_synonyms: list = None) -> dict:
        now = datetime.utcnow().isoformat()
        data = {
            "user_id": self.user_id,
            "subject_id": subject_id,
            "meaning_note": meaning_note,
            "reading_note": reading_note,
            "meaning_synonyms": meaning_synonyms,
            "created_at": now,
            "updated_at": now
        }
        result = self.client.table("study_materials").insert(data).execute()
        if not result.data:
             raise ValueError("Failed to create study material")
        return self._format_object(result.data[0], "study_material", "/study_materials")

    async def update_study_material(self, material_id: WKID, meaning_note: str = None, reading_note: str = None, meaning_synonyms: list = None) -> dict:
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

    async def sync_wanikani(self, api_key: str, mode: str = "merge") -> dict:
        """
        Sync subjects, assignments, and review_statistics from WaniKani API.
        Replaces the crawl-wanikani Edge Function.
        """
        await self.get_user()

        if mode == "overwrite":
            # Clear user data before sync (except knowledge_units which are shared)
            self.client.table("user_learning_states").delete().eq("user_id", self.user_id).execute()
            self.client.table("user_review_statistics").delete().eq("user_id", self.user_id).execute()
            self.client.table("review_logs").delete().eq("user_id", self.user_id).execute()
            self.client.table("level_progressions").delete().eq("user_id", self.user_id).execute()

        wanikani_base = settings.WANIKANI_API_URL
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Wanikani-Revision": "20170710",
        }

        types_to_sync = ["radical", "kanji", "vocabulary", "kana_vocabulary"]
        total_subjects = 0

        async with httpx.AsyncClient(timeout=60.0) as http:
            # ── Phase 1: Subjects ──
            for t in types_to_sync:
                url: Optional[str] = f"{wanikani_base}/subjects?types={t}"
                while url:
                    resp = await http.get(url, headers=headers)
                    resp.raise_for_status()
                    result = resp.json()

                    records = []
                    meanings_data = []
                    readings_data = []

                    for s in result.get("data", []):
                        d = s.get("data", {})
                        wanikani_id = s["id"]
                        records.append({
                            "wanikani_id": wanikani_id,
                            "type": s["object"],
                            "level": d.get("level"),
                            "character": d.get("characters") or d.get("character"),
                            "meaning_mnemonic": d.get("meaning_mnemonic"),
                            "reading_mnemonic": d.get("reading_mnemonic"),
                            "meaning_hint": d.get("meaning_hint"),
                            "reading_hint": d.get("reading_hint"),
                            "component_subject_ids": d.get("component_subject_ids", []),
                            "amalgamation_subject_ids": d.get("amalgamation_subject_ids", []),
                            "auxiliary_meanings": d.get("auxiliary_meanings", []),
                            "parts_of_speech": d.get("parts_of_speech", []),
                            "character_images": d.get("character_images", []),
                            "slug": d.get("slug"),
                            "lesson_position": d.get("lesson_position"),
                            "created_at": self._format_date(s.get("data_updated_at") or d.get("created_at")),
                        })

                        for m in d.get("meanings", []):
                            meanings_data.append({
                                "_wanikani_id": wanikani_id,
                                "meaning": m.get("meaning"),
                                "primary": m.get("primary", False),
                                "accepted_answer": m.get("accepted_answer", True)
                            })
                            
                        for r in d.get("readings", []):
                            readings_data.append({
                                "_wanikani_id": wanikani_id,
                                "reading": r.get("reading"),
                                "primary": r.get("primary", False),
                                "accepted_answer": r.get("accepted_answer", True),
                                "type": r.get("type")
                            })

                    if records:
                        res = self.client.table("knowledge_units").upsert(
                            records, on_conflict="wanikani_id"
                        ).execute()
                        
                        if res.data:
                            wk_id_to_ku_id = {row["wanikani_id"]: row["ku_id"] for row in res.data}
                            
                            bulk_meanings = []
                            for m in meanings_data:
                                ku_id = wk_id_to_ku_id.get(m["_wanikani_id"])
                                if ku_id:
                                    bulk_meanings.append({
                                        "ku_id": ku_id,
                                        "meaning": m["meaning"],
                                        "primary": m["primary"],
                                        "accepted_answer": m["accepted_answer"]
                                    })
                                    
                            bulk_readings = []
                            for r in readings_data:
                                ku_id = wk_id_to_ku_id.get(r["_wanikani_id"])
                                if ku_id:
                                    bulk_readings.append({
                                        "ku_id": ku_id,
                                        "reading": r["reading"],
                                        "primary": r["primary"],
                                        "accepted_answer": r["accepted_answer"],
                                        "type": r["type"]
                                    })
                                    
                            if bulk_meanings:
                                for bulk in [bulk_meanings[i:i + 500] for i in range(0, len(bulk_meanings), 500)]:
                                    ku_ids = list(set([m["ku_id"] for m in bulk]))
                                    self.client.table("subject_meanings").delete().in_("ku_id", ku_ids).execute()
                                    self.client.table("subject_meanings").insert(bulk).execute()

                            if bulk_readings:
                                for bulk in [bulk_readings[i:i + 500] for i in range(0, len(bulk_readings), 500)]:
                                    ku_ids = list(set([r["ku_id"] for r in bulk]))
                                    self.client.table("subject_readings").delete().in_("ku_id", ku_ids).execute()
                                    self.client.table("subject_readings").insert(bulk).execute()

                    total_subjects += len(result.get("data", []))
                    url = result.get("pages", {}).get("next_url")
                    if total_subjects > 25000: break

            # ── Phase 1.5: Build Mapping ──
            wk_id_to_ku_id = {}
            page_size = 1000
            offset = 0
            while True:
                ku_res = self.client.table("knowledge_units").select("wanikani_id, ku_id").range(offset, offset + page_size - 1).execute()
                if not ku_res.data: break
                for row in ku_res.data:
                    wk_id_to_ku_id[row["wanikani_id"]] = row["ku_id"]
                if len(ku_res.data) < page_size: break
                offset += page_size

            # ── Phase 2: Assignments ──
            total_assignments = 0
            url = f"{wanikani_base}/assignments"
            while url:
                resp = await http.get(url, headers=headers)
                resp.raise_for_status()
                result = resp.json()

                records = []
                for a in result.get("data", []):
                    d = a.get("data", {})
                    ku_id = wk_id_to_ku_id.get(d.get("subject_id"))
                    if ku_id:
                        records.append({
                            "user_id": self.user_id,
                            "ku_id": ku_id,
                            "wanikani_id": a["id"],
                            "srs_stage": d.get("srs_stage", 0),
                            "unlocked_at": d.get("unlocked_at"),
                            "started_at": d.get("started_at"),
                            "passed_at": d.get("passed_at"),
                            "burned_at": d.get("burned_at"),
                            "available_at": d.get("available_at"),
                            "resurrected_at": d.get("resurrected_at"),
                            "hidden": d.get("hidden", False),
                        })

                if records:
                    self.client.table("user_learning_states").upsert(records, on_conflict="user_id,ku_id").execute()

                total_assignments += len(result.get("data", []))
                url = result.get("pages", {}).get("next_url")

            # ── Phase 3: Review Statistics ──
            total_stats = 0
            url = f"{wanikani_base}/review_statistics"
            while url:
                resp = await http.get(url, headers=headers)
                resp.raise_for_status()
                result = resp.json()

                records = []
                for rs in result.get("data", []):
                    d = rs.get("data", {})
                    ku_id = wk_id_to_ku_id.get(d.get("subject_id"))
                    if ku_id:
                        records.append({
                            "user_id": self.user_id,
                            "ku_id": ku_id,
                            "wanikani_id": rs["id"],
                            "meaning_correct": d.get("meaning_correct", 0),
                            "meaning_incorrect": d.get("meaning_incorrect", 0),
                            "meaning_current_streak": d.get("meaning_current_streak", 0),
                            "reading_correct": d.get("reading_correct", 0),
                            "reading_incorrect": d.get("reading_incorrect", 0),
                            "reading_current_streak": d.get("reading_current_streak", 0),
                            "percentage_correct": d.get("percentage_correct", 0),
                            "hidden": d.get("hidden", False),
                        })

                if records:
                    self.client.table("user_review_statistics").upsert(records, on_conflict="user_id,ku_id").execute()

                total_stats += len(result.get("data", []))
                url = result.get("pages", {}).get("next_url")

            # ── Phase 4: User Level ──
            try:
                user_resp = await http.get(f"{wanikani_base}/user", headers=headers)
                wk_level = user_resp.json().get("data", {}).get("level", 1)
                self.client.table("users").update({"level": wk_level}).eq("id", self.user_id).execute()
            except: pass

        return {
            "success": True,
            "mode": mode,
            "subjects_synced": total_subjects,
            "assignments_synced": total_assignments,
            "review_statistics_synced": total_stats,
        }
