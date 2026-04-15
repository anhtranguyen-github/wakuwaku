from typing import Optional, List, Any, Union
from datetime import datetime
import json
import uuid
import logging
import httpx
from app.db import get_supabase
from app.core.config import settings
from app.schemas.hanachan_wanikani import WKID

logger = logging.getLogger(__name__)


class HanachanService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_url = "/v2"
        self.client = get_supabase()

    async def get_user(self) -> dict:
        response = self.client.table("users").select("*").eq("id", self.user_id).execute()
        
        # WaniKani default preferences
        default_preferences = {
            "lessons_autoplay_audio": False,
            "lessons_batch_size": 10,
            "reviews_autoplay_audio": False,
            "reviews_display_srs_indicator": True,
            "extra_study_autoplay_audio": False,
            "reviews_presentation_order": "shuffled",
            "lessons_presentation_order": "ascending_level_then_subject",
            "default_voice_actor_id": 1
        }

        if response.data:
            user = response.data[0]
            is_active = user.get("subscription_type") != "free"
            return {
                "object": "user",
                "url": f"{self.base_url}/user",
                "data_updated_at": self.format_date(user.get("updated_at")),
                "data": {
                    "id": str(user["id"]),
                    "username": user.get("username", "user"),
                    "level": user.get("level", 1),
                    "started_at": self.format_date(user.get("started_at") or user.get("created_at")),
                    "subscription": {
                        "active": is_active,
                        "type": user.get("subscription_type", "free"),
                        "max_level_granted": user.get("max_level", 60) if is_active else 3,
                        "period_ends_at": None
                    },
                    "current_vacation_started_at": None,
                    "preferences": (user.get("preferences") if user.get("preferences") else default_preferences)
                }
            }
        
        # Fallback for new users if not in DB yet
        return {
            "object": "user",
            "url": f"{self.base_url}/user",
            "data_updated_at": self.format_date(datetime.utcnow()),
            "data": {
                "id": str(self.user_id),
                "level": 1,
                "username": "newuser",
                "started_at": self.format_date(datetime.utcnow()),
                "profile_url": f"{settings.APP_BASE_URL}/users/{self.user_id}",
                "current_vacation_started_at": None,
                "preferences": default_preferences,
                "subscription": {
                    "active": False,
                    "max_level_granted": 3,
                    "type": "free",
                    "period_ends_at": None
                }
            }
        }

    def format_date(self, dt_val: Any) -> Optional[str]:
        if not dt_val:
            return None
        
        # If string, try to parse. If datetime, format directly.
        if isinstance(dt_val, str):
            try:
                # Handle possible Z or +00:00
                clean_str = dt_val.replace("Z", "+00:00")
                dt_obj = datetime.fromisoformat(clean_str)
            except ValueError:
                return dt_val # Fallback
        elif isinstance(dt_val, datetime):
            dt_obj = dt_val
        else:
            return str(dt_val)

        # WaniKani uses 6 decimal places for microseconds and 'Z' for UTC
        return dt_obj.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

    def format_collection(self, data: List[dict], object_type: str, url: str) -> dict:
        """
        Wraps data in WaniKani collection format.
        """
        return {
            "object": "collection",
            "url": f"{self.base_url}{url}",
            "pages": {
                "per_page": 1000,
                "next_url": None,
                "previous_url": None
            },
            "total_count": len(data),
            "data_updated_at": self.format_date(datetime.utcnow()),
            "data": data
        }

    async def get_assignments(
        self,
        available_after: Optional[datetime] = None,
        available_before: Optional[datetime] = None,
        burned: Optional[bool] = None,
        hidden: Optional[bool] = None,
        ids: Optional[List[int]] = None,
        immediately_available_for_lessons: Optional[bool] = None,
        immediately_available_for_review: Optional[bool] = None,
        in_review: Optional[bool] = None,
        levels: Optional[List[int]] = None,
        srs_stages: Optional[List[int]] = None,
        started: Optional[bool] = None,
        subject_ids: Optional[List[int]] = None,
        subject_types: Optional[List[str]] = None,
        unlocked: Optional[bool] = None,
        updated_after: Optional[datetime] = None,
    ) -> dict:
        query = self.client.table("user_learning_states").select("*, knowledge_units(*)").eq("user_id", self.user_id)
        
        # Apply filters
        if available_after:
            query = query.gte("available_at", available_after.isoformat())
        if available_before:
            query = query.lte("available_at", available_before.isoformat())
        if burned is not None:
            if burned:
                query = query.not_.is_("burned_at", "null")
            else:
                query = query.is_("burned_at", "null")
        if hidden is not None:
            query = query.eq("hidden", hidden)
        
        if immediately_available_for_lessons:
            query = query.eq("srs_stage", 0).not_.is_("unlocked_at", "null")
        
        if levels:
            query = query.filter("knowledge_units.level", "in", f"({','.join(map(str, levels))})")
            
        if srs_stages:
            query = query.filter("srs_stage", "in", f"({','.join(map(str, srs_stages))})")

        if started is not None:
            if started:
                query = query.not_.is_("started_at", "null")
            else:
                query = query.is_("started_at", "null")
        
        if subject_types:
            query = query.filter("knowledge_units.type", "in", f"({','.join([f'\"{t}\"' for t in subject_types])})")

        if unlocked is not None:
            if unlocked:
                query = query.not_.is_("unlocked_at", "null")
            else:
                query = query.is_("unlocked_at", "null")

        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())

        response = query.order("wanikani_id").limit(500).execute()
        
        data = []
        for item in response.data:
            ku = item.get("knowledge_units", {})
            if not ku: continue 
            
            if subject_ids and ku.get("wanikani_id") not in subject_ids:
                continue

            if immediately_available_for_review:
                if not (item.get("srs_stage", 0) > 0 and 
                        item.get("available_at") and 
                        datetime.fromisoformat(item["available_at"].replace("Z", "+00:00")) <= datetime.now().astimezone() and
                        not item.get("started_at")):
                    continue
            
            if in_review:
                if not (item.get("started_at") and not item.get("burned_at")):
                    continue

            assignment_id = item.get("wanikani_id") or ku.get("wanikani_id")
            if ids and assignment_id not in ids:
                continue

            data.append({
                "id": assignment_id,
                "object": "assignment",
                "url": f"{self.base_url}/assignments/{assignment_id}",
                "data_updated_at": self.format_date(item.get("updated_at")),
                "data": {
                    "available_at": self.format_date(item.get("available_at")),
                    "burned_at": self.format_date(item.get("burned_at")),
                    "created_at": self.format_date(item.get("created_at")),
                    "hidden": item.get("hidden", False),
                    "passed_at": self.format_date(item.get("passed_at")),
                    "resurrected_at": self.format_date(item.get("resurrected_at")),
                    "srs_stage": item.get("srs_stage", 0),
                    "started_at": self.format_date(item.get("started_at")),
                    "subject_id": ku.get("wanikani_id"),
                    "subject_type": ku.get("type"),
                    "unlocked_at": self.format_date(item.get("unlocked_at"))
                }
            })
            
        return self.format_collection(data, "assignment", "/assignments")

    async def get_assignment(self, assignment_id: int) -> dict:
        # We use wanikani_id as the selection criteria for assignment_id
        response = self.client.table("user_learning_states").select("*, knowledge_units(*)").eq("user_id", self.user_id).eq("knowledge_units.wanikani_id", assignment_id).execute()
        
        if not response.data:
            raise ValueError("Assignment not found")
            
        item = response.data[0]
        ku = item.get("knowledge_units", {})
        
        return {
            "id": assignment_id,
            "object": "assignment",
            "url": f"{self.base_url}/assignments/{assignment_id}",
            "data_updated_at": self.format_date(item.get("updated_at")),
            "data": {
                "available_at": self.format_date(item.get("available_at")),
                "burned_at": self.format_date(item.get("burned_at")),
                "created_at": self.format_date(item.get("created_at")),
                "hidden": item.get("hidden", False),
                "passed_at": self.format_date(item.get("passed_at")),
                "resurrected_at": self.format_date(item.get("resurrected_at")),
                "srs_stage": item.get("srs_stage", 0),
                "started_at": self.format_date(item.get("started_at")),
                "subject_id": assignment_id,
                "subject_type": ku.get("type"),
                "unlocked_at": self.format_date(item.get("unlocked_at"))
            }
        }

    async def start_assignment(self, assignment_id: WKID, started_at: Optional[datetime] = None) -> dict:
        start_time = started_at or datetime.utcnow()
        
        # We need to find the record first to get its current state
        # Supports both UUID and wanikani_id
        query = self.client.table("user_learning_states")\
            .select("*, knowledge_units(*)")\
            .eq("user_id", self.user_id)
            
        if isinstance(assignment_id, str) and "-" in str(assignment_id):
            query = query.eq("id", assignment_id)
        else:
            query = query.eq("knowledge_units.wanikani_id", assignment_id)
            
        result = query.execute()
        if not result.data:
            raise ValueError("Assignment not found")
        
        item = result.data[0]
        
        update_data = {
            "started_at": start_time.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # If it was in stage 0 (unstarted), move to stage 1 manually if WaniKani does that
        # (WaniKani assignments transition from stage 0 to stage 1 upon starting/reviewing)
        if item.get("srs_stage") == 0:
            update_data["srs_stage"] = 1
            
        update_result = self.client.table("user_learning_states")\
            .update(update_data)\
            .eq("id", item["id"])\
            .select("*, knowledge_units(*)")\
            .execute()
            
        if not update_result.data:
            raise RuntimeError("Failed to update assignment")
            
        updated_item = update_result.data[0]
        ku = updated_item.get("knowledge_units", {})
        wid = ku.get("wanikani_id")
        
        return {
            "id": wid,
            "object": "assignment",
            "url": f"{self.base_url}/assignments/{wid}",
            "data_updated_at": self.format_date(updated_item.get("updated_at")),
            "data": {
                "available_at": self.format_date(updated_item.get("available_at")),
                "burned_at": self.format_date(updated_item.get("burned_at")),
                "created_at": self.format_date(updated_item.get("created_at")),
                "hidden": updated_item.get("hidden", False),
                "passed_at": self.format_date(updated_item.get("passed_at")),
                "resurrected_at": self.format_date(updated_item.get("resurrected_at")),
                "srs_stage": updated_item.get("srs_stage", 0),
                "started_at": self.format_date(updated_item.get("started_at")),
                "subject_id": wid,
                "subject_type": ku.get("type"),
                "unlocked_at": self.format_date(updated_item.get("unlocked_at"))
            }
        }

    async def get_level_progressions(
        self,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
    ) -> dict:
        query = self.client.table("level_progressions").select("*").eq("user_id", self.user_id)
        
        if ids:
            query = query.in_("id", ids)
        if updated_after:
            query = query.gte("created_at", updated_after.isoformat())
            
        response = query.order("created_at", desc=False).limit(500).execute()
        rows = response.data
        
        data = []
        for item in rows:
            data.append({
                "id": str(item["id"]),
                "object": "level_progression",
                "url": f"{self.base_url}/level_progressions/{item['id']}",
                "data_updated_at": self.format_date(item.get("created_at")),
                "data": {
                    "level": item["level"],
                    "created_at": self.format_date(item.get("created_at")),
                    "unlocked_at": self.format_date(item.get("unlocked_at")),
                    "started_at": self.format_date(item.get("started_at")),
                    "passed_at": self.format_date(item.get("passed_at")),
                    "completed_at": self.format_date(item.get("completed_at")),
                    "abandoned_at": self.format_date(item.get("abandoned_at"))
                }
            })
        
        return {
            "object": "collection",
            "url": f"{self.base_url}/level_progressions",
            "data_updated_at": datetime.utcnow().isoformat(),
            "data": data,
            "pages": {"next_url": None, "previous_url": None, "per_page": 500},
            "total_count": len(data)
        }

    async def get_level_progression(self, progression_id: str) -> dict:
        response = self.client.table("level_progressions")\
            .select("*")\
            .eq("id", progression_id)\
            .eq("user_id", self.user_id)\
            .single()\
            .execute()
        
        item = response.data
        if not item:
            raise ValueError("Level progression not found")
        
        return {
            "id": str(item["id"]),
            "object": "level_progression",
            "url": f"{self.base_url}/level_progressions/{item['id']}",
            "data_updated_at": self.format_date(item.get("created_at")),
            "data": {
                "level": item["level"],
                "created_at": self.format_date(item.get("created_at")),
                "unlocked_at": self.format_date(item.get("unlocked_at")),
                "started_at": self.format_date(item.get("started_at")),
                "passed_at": self.format_date(item.get("passed_at")),
                "completed_at": self.format_date(item.get("completed_at")),
                "abandoned_at": self.format_date(item.get("abandoned_at"))
            }
        }

    async def get_resets(
        self,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
    ) -> dict:
        # Note: 'resets' table missing in target Supabase schema. 
        # Returning empty collection to maintain API parity for now.
        return {
            "object": "collection",
            "url": f"{self.base_url}/resets",
            "data_updated_at": datetime.utcnow().isoformat(),
            "data": [],
            "pages": {"next_url": None, "previous_url": None, "per_page": 500},
            "total_count": 0
        }

    async def get_reset(self, reset_id: str) -> dict:
        raise ValueError("Reset not found")

    # NOTE: get_spaced_repetition_systems is defined later in this file (with interval_unit fields)
    # The single-item accessor is also defined there as get_spaced_repetition_system.

    async def get_reviews(
        self,
        ids: Optional[List[str]] = None,
        updated_after: Optional[datetime] = None,
        assignment_ids: Optional[List[int]] = None,
        subject_ids: Optional[List[int]] = None,
    ) -> dict:
        # Mapping 'reviews' to 'review_logs' in Supabase
        # We join with knowledge_units for subject_id and user_learning_states for assignment_id
        query = self.client.table("review_logs")\
            .select("*, knowledge_units(wanikani_id), user_learning_states!review_logs_user_learning_states_fkey(wanikani_id)")\
            .eq("user_id", self.user_id)
        
        # Note: If no FK exists between review_logs and user_learning_states, we fallback to separate lookup
        # Based on schema check, they both have ku_id and user_id. 
        # But let's simplify and just fetch necessary IDs if join fails or is complex.
        
        # Better: select with nested knowledge_unit
        query = self.client.table("review_logs")\
            .select("*, knowledge_units(wanikani_id)")\
            .eq("user_id", self.user_id)

        if ids:
            query = query.in_("id", ids)
        if updated_after:
            query = query.gte("created_at", updated_after.isoformat())
        if subject_ids:
            sb_subjects = self.client.table("knowledge_units").select("ku_id").in_("wanikani_id", subject_ids).execute()
            ku_ids = [s["ku_id"] for s in sb_subjects.data]
            if ku_ids:
                query = query.in_("ku_id", ku_ids)
            else:
                return self.format_collection([], "review", "/reviews")
            
        response = query.order("created_at", desc=False).limit(500).execute()
        rows = response.data
        
        # Populate assignment IDs separately to avoid complex joins if not explicitly related by FK in Supabase
        ku_ids = list(set(item["ku_id"] for item in rows if item.get("ku_id")))
        assignments_map = {}
        if ku_ids:
            a_res = self.client.table("user_learning_states").select("ku_id, wanikani_id").eq("user_id", self.user_id).in_("ku_id", ku_ids).execute()
            assignments_map = {a["ku_id"]: a["wanikani_id"] for a in a_res.data}

        data = []
        for item in rows:
            ku = item.get("knowledge_units") or {}
            subject_id = ku.get("wanikani_id", 0)
            assignment_id = assignments_map.get(item.get("ku_id"), 0)
            metadata = item.get("metadata") or {}
            
            data.append({
                "id": str(item["id"]),
                "object": "review",
                "url": f"{self.base_url}/reviews/{item['id']}",
                "data_updated_at": self.format_date(item.get("created_at")),
                "data": {
                    "created_at": self.format_date(item.get("created_at")),
                    "assignment_id": int(assignment_id) if assignment_id else None,
                    "spaced_repetition_system_id": 1,
                    "subject_id": int(subject_id) if subject_id else None,
                    "starting_srs_stage": item.get("old_srs_stage", 0),
                    "ending_srs_stage": item.get("new_srs_stage", 0),
                    "incorrect_meaning_answers": metadata.get("incorrect_meaning_answers", 0),
                    "incorrect_reading_answers": metadata.get("incorrect_reading_answers", 0)
                }
            })
        
        return self.format_collection(data, "review", "/reviews")

    async def create_review(
        self,
        assignment_id: WKID,
        incorrect_meaning_answers: int,
        incorrect_reading_answers: int,
        created_at: Optional[datetime] = None
    ) -> dict:
        review_time = created_at or datetime.utcnow()
        
        # 1. Get current learning state (assignment)
        # Supports both integer (mapped from memory/cache) and UUID strings
        query = self.client.table("user_learning_states").select("*, knowledge_units(*)").eq("user_id", self.user_id)
        if isinstance(assignment_id, str) and "-" in assignment_id:
            query = query.eq("id", assignment_id)
        else:
            # If it's an integer, we might need a mapping or lookup by ku_id if assignment_id was wanikani_id
            # In Hanachan, often assignment_id (API) maps to state.id (Supabase)
            # Try to match by ID first
            query = query.eq("id", str(assignment_id))
            
        result = query.execute()
        if not result.data:
            # Fallback: try looking up by ku_id if assignment_id was a wanikani_id
            fallback = self.client.table("user_learning_states")\
                .select("*, knowledge_units(*)")\
                .eq("user_id", self.user_id)\
                .eq("knowledge_units.wanikani_id", assignment_id)\
                .execute()
            if not fallback.data:
                raise ValueError(f"Assignment not found: {assignment_id}")
            state = fallback.data[0]
        else:
            state = result.data[0]
            
        starting_srs_stage = state.get("srs_stage", 0)
        ending_srs_stage = starting_srs_stage
        
        # Calculate new SRS stage (simplified WK logic)
        if incorrect_meaning_answers == 0 and incorrect_reading_answers == 0:
            ending_srs_stage = min(starting_srs_stage + 1, 9)
        elif starting_srs_stage > 0:
            # Standard WK punishment logic is more complex, but we maintain parity with existing 450:451
            ending_srs_stage = max(starting_srs_stage - 1, 0)

        # 2. Insert Review Log
        review_data = {
            "user_id": self.user_id,
            "ku_id": state["ku_id"],
            "review_type": "standard",  # Hanachan internal type
            "score": 1 if (incorrect_meaning_answers == 0 and incorrect_reading_answers == 0) else 0,
            "old_srs_stage": starting_srs_stage,
            "new_srs_stage": ending_srs_stage,
            "incorrect_meaning_answers": incorrect_meaning_answers,
            "incorrect_reading_answers": incorrect_reading_answers,
            "created_at": review_time.isoformat()
        }
        
        # Check if table has specific columns from old logic
        # Based on schema.sql, we have starting_srs_stage, ending_srs_stage, etc.
        # review_logs in Supabase seems to follow this.
        
        log_result = self.client.table("review_logs").insert(review_data).execute()
        if not log_result.data:
            raise RuntimeError("Failed to insert review log")
        review_log = log_result.data[0]

        # 3. Update Learning State
        # Calculate interval (Existing logic: stage * 24h)
        available_interval = ending_srs_stage * 24 * 3600
        available_at = datetime.fromtimestamp(review_time.timestamp() + available_interval)
        
        update_data = {
            "srs_stage": ending_srs_stage,
            "available_at": available_at.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # If successfully moved to stage 1+, set started_at if not present
        if ending_srs_stage > 0 and not state.get("started_at"):
            update_data["started_at"] = review_time.isoformat()
            
        # If reached stage 9, set burned_at
        if ending_srs_stage == 9 and not state.get("burned_at"):
            update_data["burned_at"] = review_time.isoformat()

        self.client.table("user_learning_states").update(update_data).eq("id", state["id"]).execute()

        # 4. Update Review Statistics
        stats_query = self.client.table("user_review_statistics")\
            .select("*")\
            .eq("user_id", self.user_id)\
            .eq("ku_id", state["ku_id"])\
            .execute()
            
        if stats_query.data:
            stat = stats_query.data[0]
            new_meaning_correct = stat.get("meaning_correct", 0) + (1 if incorrect_meaning_answers == 0 else 0)
            new_meaning_incorrect = stat.get("meaning_incorrect", 0) + (1 if incorrect_meaning_answers > 0 else 0)
            new_reading_correct = stat.get("reading_correct", 0) + (1 if incorrect_reading_answers == 0 else 0)
            new_reading_incorrect = stat.get("reading_incorrect", 0) + (1 if incorrect_reading_answers > 0 else 0)
            
            total = new_meaning_correct + new_meaning_incorrect + new_reading_correct + new_reading_incorrect
            percentage = int((new_meaning_correct + new_reading_correct) / total * 100) if total > 0 else 0
            
            stat_update = {
                "meaning_correct": new_meaning_correct,
                "meaning_incorrect": new_meaning_incorrect,
                "reading_correct": new_reading_correct,
                "reading_incorrect": new_reading_incorrect,
                "percentage_correct": percentage,
                "updated_at": datetime.utcnow().isoformat()
            }
            self.client.table("user_review_statistics").update(stat_update).eq("id", stat["id"]).execute()
        else:
            # Create new statistic entry if missing
            new_stat = {
                "user_id": self.user_id,
                "ku_id": state["ku_id"],
                "meaning_correct": 1 if incorrect_meaning_answers == 0 else 0,
                "meaning_incorrect": 1 if incorrect_meaning_answers > 0 else 0,
                "reading_correct": 1 if incorrect_reading_answers == 0 else 0,
                "reading_incorrect": 1 if incorrect_reading_answers > 0 else 0,
                "percentage_correct": 100 if (incorrect_meaning_answers == 0 and incorrect_reading_answers == 0) else 0
            }
            self.client.table("user_review_statistics").insert(new_stat).execute()

        # 5. Format Response (WK Parity)
        return {
            "id": str(review_log["id"]),
            "object": "review",
            "url": f"{self.base_url}/reviews/{review_log['id']}",
            "data_updated_at": review_log.get("created_at"),
            "data": {
                "created_at": review_log.get("created_at"),
                "assignment_id": assignment_id,
                "spaced_repetition_system_id": 1, # Default SRS
                "subject_id": state["knowledge_units"].get("wanikani_id"),
                "starting_srs_stage": starting_srs_stage,
                "ending_srs_stage": ending_srs_stage,
                "incorrect_meaning_answers": incorrect_meaning_answers,
                "incorrect_reading_answers": incorrect_reading_answers
            }
        }

    async def get_review(self, review_id: str) -> dict:
        response = self.client.table("review_logs")\
            .select("*")\
            .eq("id", review_id)\
            .eq("user_id", self.user_id)\
            .single()\
            .execute()
        
        item = response.data
        if not item:
            raise ValueError("Review not found")
        
        return {
            "id": str(item["id"]),
            "object": "review",
            "url": f"{self.base_url}/reviews/{item['id']}",
            "data_updated_at": self.format_date(item.get("created_at")),
            "data": {
                "created_at": self.format_date(item.get("created_at")),
                "assignment_id": str(item.get("assignment_id", "")),
                "spaced_repetition_system_id": 1,
                "subject_id": item.get("subject_id", 0),
                "starting_srs_stage": item.get("old_srs_stage", 0),
                "ending_srs_stage": item.get("new_srs_stage", 0),
                "incorrect_meaning_answers": 0,
                "incorrect_reading_answers": 0
            }
        }

    async def get_review_statistics(
        self,
        ids: Optional[List[str]] = None,
        updated_after: Optional[datetime] = None,
        hidden: Optional[bool] = None,
        subject_ids: Optional[List[int]] = None,
        subject_types: Optional[List[str]] = None,
        percentages_greater_than: Optional[int] = None,
        percentages_less_than: Optional[int] = None,
    ) -> dict:
        query = self.client.table("user_review_statistics").select("*, knowledge_units(*)").eq("user_id", self.user_id)
        
        if ids:
            query = query.in_("id", ids)
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
        if hidden is not None:
            query = query.eq("hidden", hidden)
        if subject_ids:
            # Map wanikani_ids to ku_ids first
            sb_subjects = self.client.table("knowledge_units").select("ku_id").in_("wanikani_id", subject_ids).execute()
            ku_ids = [s["ku_id"] for s in sb_subjects.data]
            if ku_ids:
                query = query.in_("ku_id", ku_ids)
            else:
                return {
                    "object": "collection",
                    "url": f"{self.base_url}/review_statistics",
                    "data_updated_at": datetime.utcnow().isoformat(),
                    "data": [],
                    "total_count": 0
                }
        if subject_types:
            query = query.in_("knowledge_units.type", subject_types)
            
        response = query.execute()
        rows = response.data
        
        data = []
        for item in rows:
            percentage = item.get("percentage_correct", 0)
            
            if percentages_greater_than is not None and percentage <= percentages_greater_than:
                continue
            if percentages_less_than is not None and percentage >= percentages_less_than:
                continue
            
            ku = item.get("knowledge_units") or {}
            
            data.append({
                "id": str(item["id"]),
                "object": "review_statistic",
                "url": f"{self.base_url}/review_statistics/{item['id']}",
                "data_updated_at": self.format_date(item.get("updated_at")),
                "data": {
                    "created_at": self.format_date(item.get("updated_at")), # Approximation
                    "hidden": item.get("hidden", False),
                    "meaning_correct": item.get("meaning_correct", 0),
                    "meaning_current_streak": item.get("meaning_current_streak", 0),
                    "meaning_incorrect": item.get("meaning_incorrect", 0),
                    "meaning_max_streak": item.get("meaning_longest_streak", 0),
                    "reading_correct": item.get("reading_correct", 0),
                    "reading_current_streak": item.get("reading_current_streak", 0),
                    "reading_incorrect": item.get("reading_incorrect", 0),
                    "reading_max_streak": item.get("reading_longest_streak", 0),
                    "percentage_correct": percentage,
                    "subject_id": ku.get("wanikani_id", 0),
                    "subject_type": ku.get("type", "vocabulary")
                }
            })
        
        return self.format_collection(data, "review_statistic", "/review_statistics")

    async def get_review_statistic(self, statistic_id: str) -> dict:
        response = self.client.table("user_review_statistics")\
            .select("*, knowledge_units(*)")\
            .eq("id", statistic_id)\
            .eq("user_id", self.user_id)\
            .single()\
            .execute()
        
        item = response.data
        if not item:
            raise ValueError("Review statistic not found")
        
        ku = item.get("knowledge_units") or {}
        
        return {
            "id": str(item["id"]),
            "object": "review_statistic",
            "url": f"{self.base_url}/review_statistics/{item['id']}",
            "data_updated_at": self.format_date(item.get("updated_at")),
            "data": {
                "created_at": self.format_date(item.get("updated_at")),
                "hidden": item.get("hidden", False),
                "meaning_correct": item.get("meaning_correct", 0),
                "meaning_current_streak": item.get("meaning_current_streak", 0),
                "meaning_incorrect": item.get("meaning_incorrect", 0),
                "meaning_max_streak": item.get("meaning_longest_streak", 0),
                "reading_correct": item.get("reading_correct", 0),
                "reading_current_streak": item.get("reading_current_streak", 0),
                "reading_incorrect": item.get("reading_incorrect", 0),
                "reading_max_streak": item.get("reading_longest_streak", 0),
                "percentage_correct": item.get("percentage_correct", 0),
                "subject_id": ku.get("wanikani_id", 0),
                "subject_type": ku.get("type", "vocabulary")
            }
        }

    async def get_spaced_repetition_systems(
        self,
        hidden: Optional[bool] = None,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
        subject_ids: Optional[List[int]] = None,
        subject_types: Optional[List[str]] = None,
    ) -> dict:
        # Note: spaced_repetition_systems missing in Supabase. 
        # Returning default WaniKani-like SRS for parity.
        stages = [
            {"position": 0, "interval": None, "interval_unit": None},
            {"position": 1, "interval": 14400, "interval_unit": "seconds"},
            {"position": 2, "interval": 28800, "interval_unit": "seconds"},
            {"position": 3, "interval": 86400, "interval_unit": "seconds"},
            {"position": 4, "interval": 172800, "interval_unit": "seconds"},
            {"position": 5, "interval": 604800, "interval_unit": "seconds"},
            {"position": 6, "interval": 1209600, "interval_unit": "seconds"},
            {"position": 7, "interval": 2592000, "interval_unit": "seconds"},
            {"position": 8, "interval": 10368000, "interval_unit": "seconds"},
            {"position": 9, "interval": None, "interval_unit": None}
        ]
        
        data = [{
            "id": 1,
            "object": "spaced_repetition_system",
            "url": f"{self.base_url}/spaced_repetition_systems/1",
            "data_updated_at": datetime.utcnow().isoformat(),
            "data": {
                "created_at": "2017-07-10T00:00:00.000000Z",
                "name": "WaniKani SRS",
                "description": "The default WaniKani Spaced Repetition System",
                "unlocking_stage_position": 0,
                "starting_stage_position": 1,
                "passing_stage_position": 5,
                "burning_stage_position": 9,
                "stages": stages
            }
        }]
        
        return {
            "object": "collection",
            "url": f"{self.base_url}/spaced_repetition_systems",
            "data_updated_at": datetime.utcnow().isoformat(),
            "data": data,
            "pages": {"next_url": None, "previous_url": None, "per_page": 500},
            "total_count": len(data)
        }

    async def get_spaced_repetition_system(self, srs_id: int) -> dict:
        if srs_id != 1:
            raise ValueError("Spaced repetition system not found")
            
        stages = [
            {"position": 0, "interval": None, "interval_unit": None},
            {"position": 1, "interval": 14400, "interval_unit": "seconds"},
            {"position": 2, "interval": 28800, "interval_unit": "seconds"},
            {"position": 3, "interval": 86400, "interval_unit": "seconds"},
            {"position": 4, "interval": 172800, "interval_unit": "seconds"},
            {"position": 5, "interval": 604800, "interval_unit": "seconds"},
            {"position": 6, "interval": 1209600, "interval_unit": "seconds"},
            {"position": 7, "interval": 2592000, "interval_unit": "seconds"},
            {"position": 8, "interval": 10368000, "interval_unit": "seconds"},
            {"position": 9, "interval": None, "interval_unit": None}
        ]
        
        return {
            "id": 1,
            "object": "spaced_repetition_system",
            "url": f"{self.base_url}/spaced_repetition_systems/1",
            "data_updated_at": datetime.utcnow().isoformat(),
            "data": {
                "created_at": "2017-07-10T00:00:00.000000Z",
                "name": "WaniKani SRS",
                "description": "The default WaniKani Spaced Repetition System",
                "unlocking_stage_position": 0,
                "starting_stage_position": 1,
                "passing_stage_position": 5,
                "burning_stage_position": 9,
                "stages": stages
            }
        }
    
    async def get_study_materials(
        self,
        subject_ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None
    ) -> dict:
        query = self.client.table("study_materials").select("*").eq("user_id", self.user_id)
        if subject_ids:
            # map subject_ids to ku_ids
            sb_subjects = self.client.table("knowledge_units").select("ku_id").in_("wanikani_id", subject_ids).execute()
            ku_ids = [s["ku_id"] for s in sb_subjects.data]
            if ku_ids:
                query = query.in_("ku_id", ku_ids)
            else:
                return {
                    "object": "collection",
                    "url": f"{self.base_url}/study_materials",
                    "data_updated_at": datetime.utcnow().isoformat(),
                    "data": [],
                    "pages": {"next_url": None, "previous_url": None, "per_page": 500},
                    "total_count": 0
                }
        if updated_after:
            query = query.gte("created_at", updated_after.isoformat())
            
        response = query.execute()
        data = response.data
        
        return {
            "object": "collection",
            "url": f"{self.base_url}/study_materials",
            "data_updated_at": datetime.utcnow().isoformat(),
            "data": data,
            "pages": {"next_url": None, "previous_url": None, "per_page": 500},
            "total_count": len(data)
        }

    async def create_study_material(
        self,
        subject_id: WKID,
        meaning_note: Optional[str] = None,
        reading_note: Optional[str] = None,
        meaning_synonyms: Optional[List[str]] = None
    ) -> dict:
        # Lookup knowledge unit
        ku_query = self.client.table("knowledge_units").select("*")
        if isinstance(subject_id, str) and "-" in subject_id:
            ku_query = ku_query.eq("ku_id", subject_id)
        else:
            ku_query = ku_query.eq("wanikani_id", subject_id)
            
        ku_result = ku_query.execute()
        if not ku_result.data:
            raise ValueError(f"Subject not found: {subject_id}")
        subject = ku_result.data[0]
        
        insert_data = {
            "user_id": self.user_id,
            "ku_id": subject["ku_id"],
            "meaning_note": meaning_note,
            "reading_note": reading_note,
            "meaning_synonyms": meaning_synonyms or []
        }
        
        result = self.client.table("user_study_materials").insert(insert_data).execute()
        if not result.data:
            raise RuntimeError("Failed to create study material")
        item = result.data[0]
        
        return {
            "id": str(item["id"]),
            "object": "study_material",
            "url": f"{self.base_url}/study_materials/{item['id']}",
            "data_updated_at": item.get("updated_at"),
            "data": {
                "created_at": item.get("created_at"),
                "hidden": item.get("hidden", False),
                "meaning_note": item.get("meaning_note"),
                "meaning_synonyms": item.get("meaning_synonyms", []),
                "reading_note": item.get("reading_note"),
                "subject_id": subject["wanikani_id"],
                "subject_type": subject.get("type", "vocabulary")
            }
        }

    async def get_study_material(self, material_id: WKID) -> dict:
        result = self.client.table("user_study_materials")\
            .select("*, knowledge_units(*)")\
            .eq("user_id", self.user_id)\
            .eq("id" if "-" in str(material_id) else "id", str(material_id))\
            .execute()
            
        if not result.data:
            raise ValueError("Study material not found")
            
        item = result.data[0]
        return {
            "id": str(item["id"]),
            "object": "study_material",
            "url": f"{self.base_url}/study_materials/{item['id']}",
            "data_updated_at": item.get("updated_at"),
            "data": {
                "created_at": item.get("created_at"),
                "hidden": item.get("hidden", False),
                "meaning_note": item.get("meaning_note"),
                "meaning_synonyms": item.get("meaning_synonyms", []),
                "reading_note": item.get("reading_note"),
                "subject_id": item["knowledge_units"].get("wanikani_id"),
                "subject_type": item["knowledge_units"].get("type", "vocabulary")
            }
        }

    async def update_study_material(
        self,
        material_id: WKID,
        meaning_note: Optional[str] = None,
        reading_note: Optional[str] = None,
        meaning_synonyms: Optional[List[str]] = None
    ) -> dict:
        update_data = {}
        if meaning_note is not None:
            update_data["meaning_note"] = meaning_note
        if reading_note is not None:
            update_data["reading_note"] = reading_note
        if meaning_synonyms is not None:
            update_data["meaning_synonyms"] = meaning_synonyms
            
        if not update_data:
            raise ValueError("No fields to update")
            
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = self.client.table("user_study_materials")\
            .update(update_data)\
            .eq("id", str(material_id))\
            .eq("user_id", self.user_id)\
            .select("*, knowledge_units(*)")\
            .execute()
            
        if not result.data:
            raise ValueError("Study material not found")
            
        item = result.data[0]
        
        return {
            "id": str(item["id"]),
            "object": "study_material",
            "url": f"{self.base_url}/study_materials/{item['id']}",
            "data_updated_at": item.get("updated_at"),
            "data": {
                "created_at": item.get("created_at"),
                "hidden": item.get("hidden", False),
                "meaning_note": item.get("meaning_note"),
                "meaning_synonyms": item.get("meaning_synonyms", []),
                "reading_note": item.get("reading_note"),
                "subject_id": item["knowledge_units"].get("wanikani_id"),
                "subject_type": item["knowledge_units"].get("type", "vocabulary")
            }
        }

    async def get_summary(self) -> dict:
        result = self.client.table("user_learning_states")\
            .select("*, knowledge_units(wanikani_id, level, type)")\
            .eq("user_id", self.user_id)\
            .execute()
            
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        now_str = self.format_date(now)

        # Store lessons as objects for sorting
        lesson_items = []
        review_buckets = {now_str: set()}

        for item in result.data:
            srs_stage = item.get("srs_stage", 0)
            unlocked_at = item.get("unlocked_at")
            started_at = item.get("started_at")
            burned_at = item.get("burned_at")
            available_at_str = item.get("available_at")
            
            ku = item.get("knowledge_units", {})
            if not ku: continue
            
            subject_id = ku.get("wanikani_id")
            level = ku.get("level", 0)
            subject_type = ku.get("type", "vocabulary")
            
            if srs_stage == 0 and unlocked_at and not started_at:
                lesson_items.append({
                    "id": subject_id,
                    "level": level,
                    "type": subject_type
                })
            
            if srs_stage > 0 and started_at and not burned_at and available_at_str:
                avail_dt = datetime.fromisoformat(available_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                if avail_dt <= now:
                    review_buckets[now_str].add(subject_id)
                else:
                    bucket_key = self.format_date(avail_dt.replace(minute=0, second=0, microsecond=0))
                    if bucket_key not in review_buckets:
                        review_buckets[bucket_key] = set()
                    review_buckets[bucket_key].add(subject_id)

        # WaniKani lesson order: Level ASC, Type (Radical < Kanji < Vocab)
        type_order = {"radical": 1, "kanji": 2, "vocabulary": 3}
        lesson_items.sort(key=lambda x: (x["level"], type_order.get(x["type"], 99), x["id"]))
        lesson_subject_ids = [l["id"] for l in lesson_items]

        lessons = [{"available_at": now_str, "subject_ids": lesson_subject_ids}]
        
        reviews = []
        for key in sorted(review_buckets.keys()):
            reviews.append({
                "available_at": key,
                "subject_ids": sorted(list(review_buckets[key]))
            })

        # WaniKani shows the next reviews key if there are items in future buckets
        future_reviews = [k for k in sorted(review_buckets.keys()) if k > now_str]
        next_reviews_at = future_reviews[0] if future_reviews else None

        return {
            "object": "report",
            "url": f"{self.base_url}/summary",
            "data_updated_at": self.format_date(datetime.utcnow()),
            "data": {
                "lessons": lessons,
                "next_reviews_at": next_reviews_at,
                "reviews": reviews
            }
        }

    async def get_subjects(
        self,
        updated_after: Optional[datetime] = None,
    ) -> dict:
        query = self.client.table("knowledge_units").select("*, meanings:subject_meanings(*), readings:subject_readings(*)").order("wanikani_id")
        if updated_after:
            query = query.gte("updated_at", updated_after.isoformat())
            
        result = query.limit(500).execute()
        
        data = []
        for item in result.data:
            subject_type = item.get("type", "vocabulary")
            wanikani_id = item.get("wanikani_id")
            url = f"{self.base_url}/subjects/{wanikani_id}"
            
            meanings = [
                {
                    "meaning": m["meaning"],
                    "primary": m["primary"],
                    "accepted_answer": m["accepted_answer"]
                } for m in item.get("meanings", [])
            ]
            
            # Generate slug if missing
            slug = item.get("slug")
            if not slug:
                primary_meaning = next((m["meaning"] for m in meanings if m["primary"]), "")
                slug = primary_meaning.lower().replace(" ", "-") if primary_meaning else ""
            
            # Generate document_url
            subject_type_plural = f"{subject_type}s" if subject_type != "vocabulary" else "vocabulary"
            document_url = f"https://www.wanikani.com/{subject_type_plural}/{slug}"

            base_data = {
                "level": item.get("level", 1),
                "slug": slug,
                "hidden_at": self.format_date(item.get("hidden_at")),
                "document_url": document_url,
                "characters": item.get("character"),
                "meaning_mnemonic": item.get("meaning_mnemonic", ""),
                "meanings": meanings,
                "auxiliary_meanings": item.get("auxiliary_meanings", []),
                "lesson_position": item.get("lesson_position", 0),
                "spaced_repetition_system_id": 1,
                "created_at": self.format_date(item.get("created_at"))
            }
            
            if subject_type == "radical":
                data.append({
                    "id": wanikani_id,
                    "object": "radical",
                    "url": url,
                    "data_updated_at": self.format_date(item.get("updated_at")),
                    "data": {
                        **base_data,
                        "amalgamation_subject_ids": item.get("amalgamation_subject_ids", []),
                        "character_images": item.get("character_images", [])
                    }
                })
            elif subject_type == "kanji":
                data.append({
                    "id": wanikani_id,
                    "object": "kanji",
                    "url": url,
                    "data_updated_at": self.format_date(item.get("updated_at")),
                    "data": {
                        **base_data,
                        "amalgamation_subject_ids": item.get("amalgamation_subject_ids", []),
                        "component_subject_ids": item.get("component_subject_ids", []),
                        "meaning_hint": item.get("meaning_hint"),
                        "reading_hint": item.get("reading_hint"),
                        "reading_mnemonic": item.get("reading_mnemonic", ""),
                        "readings": [
                            {
                                "reading": r["reading"],
                                "primary": r["primary"],
                                "accepted_answer": r["accepted_answer"],
                                "type": r["type"]
                            } for r in item.get("readings", [])
                        ],
                        "visually_similar_subject_ids": item.get("visually_similar_subject_ids", [])
                    }
                })
            else:
                data.append({
                    "id": wanikani_id,
                    "object": subject_type,
                    "url": url,
                    "data_updated_at": self.format_date(item.get("updated_at")),
                    "data": {
                        **base_data,
                        "component_subject_ids": item.get("component_subject_ids", []),
                        "meaning_hint": item.get("meaning_hint"),
                        "reading_hint": item.get("reading_hint"),
                        "reading_mnemonic": item.get("reading_mnemonic", ""),
                        "readings": [
                            {
                                "reading": r["reading"],
                                "primary": r["primary"],
                                "accepted_answer": r["accepted_answer"]
                            } for r in item.get("readings", [])
                        ],
                        "context_sentences": item.get("context_sentences", []),
                        "parts_of_speech": item.get("parts_of_speech", []),
                        "pronunciation_audios": item.get("pronunciation_audios", [])
                    }
                })
                
        return self.format_collection(data, "subject", "/subjects")

    async def get_subject(self, subject_id: WKID) -> dict:
        query = self.client.table("knowledge_units").select("*, meanings:subject_meanings(*), readings:subject_readings(*)")
        if isinstance(subject_id, str) and "-" in str(subject_id):
            query = query.eq("ku_id", subject_id)
        else:
            query = query.eq("wanikani_id", subject_id)
            
        result = query.execute()
        if not result.data:
            raise ValueError("Subject not found")
            
        item = result.data[0]
        # Recursively call get_subjects with filter or manually format?
        # Faster to manually format this single item
        subject_type = item.get("type", "vocabulary")
        wanikani_id = item.get("wanikani_id")
        url = f"{self.base_url}/subjects/{wanikani_id}"
        
        meanings = [
            {
                "meaning": m["meaning"],
                "primary": m["primary"],
                "accepted_answer": m["accepted_answer"]
            } for m in item.get("meanings", [])
        ]
        
        slug = item.get("slug")
        if not slug:
            primary_meaning = next((m["meaning"] for m in meanings if m["primary"]), "")
            slug = primary_meaning.lower().replace(" ", "-") if primary_meaning else ""
        
        subject_type_plural = f"{subject_type}s" if subject_type != "vocabulary" else "vocabulary"
        document_url = f"https://www.wanikani.com/{subject_type_plural}/{slug}"

        base_data = {
            "amalgamation_subject_ids": item.get("amalgamation_subject_ids", []),
            "auxiliary_meanings": item.get("auxiliary_meanings", []),
            "characters": item.get("character"),
            "character_images": item.get("character_images", []),
            "created_at": self.format_date(item.get("created_at") or datetime.utcnow()),
            "document_url": document_url,
            "hidden_at": self.format_date(item.get("hidden_at")),
            "lesson_position": item.get("lesson_position", 0),
            "level": item.get("level", 1),
            "meaning_mnemonic": item.get("meaning_mnemonic", ""),
            "meanings": meanings,
            "slug": slug,
            "spaced_repetition_system_id": item.get("spaced_repetition_system_id", 1)
        }

        specific_data = {}
        if subject_type == "radical":
            specific_data = {
                "amalgamation_subject_ids": item.get("amalgamation_subject_ids", [])
            }
        elif subject_type == "kanji":
            specific_data = {
                "component_subject_ids": item.get("component_subject_ids", []),
                "meaning_hint": item.get("meaning_hint"),
                "reading_hint": item.get("reading_hint"),
                "reading_mnemonic": item.get("reading_mnemonic", ""),
                "readings": [
                    {
                        "reading": r["reading"],
                        "primary": r["primary"],
                        "accepted_answer": r["accepted_answer"],
                        "type": r.get("type", "onyomi")
                    } for r in item.get("readings", [])
                ],
                "visually_similar_subject_ids": item.get("visually_similar_subject_ids", [])
            }
        else:
            specific_data = {
                "component_subject_ids": item.get("component_subject_ids", []),
                "meaning_hint": item.get("meaning_hint"),
                "reading_hint": item.get("reading_hint"),
                "reading_mnemonic": item.get("reading_mnemonic", ""),
                "readings": [
                    {
                        "reading": r["reading"],
                        "primary": r["primary"],
                        "accepted_answer": r["accepted_answer"]
                    } for r in item.get("readings", [])
                ],
                "context_sentences": item.get("context_sentences", []),
                "parts_of_speech": item.get("parts_of_speech", []),
                "pronunciation_audios": item.get("pronunciation_audios", [])
            }

        return {
            "id": wanikani_id,
            "object": subject_type,
            "url": url,
            "data_updated_at": self.format_date(item.get("updated_at") or datetime.utcnow()),
            "data": {
                **base_data,
                **specific_data
            }
        }
    async def sync_wanikani(self, api_key: str, subject_type: Optional[str] = None) -> dict:
        """
        Sync subjects, assignments, and review_statistics from WaniKani API.
        Replaces the crawl-wanikani Edge Function.
        """
        wanikani_base = settings.WANIKANI_API_URL
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Wanikani-Revision": "20170710",
        }

        types_to_sync = [subject_type] if subject_type else ["radical", "kanji", "vocabulary", "kana_vocabulary"]
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
                            "created_at": self.format_date(s.get("data_updated_at") or d.get("created_at")),
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
                        
                        if hasattr(res, "error") and res.error:
                            logger.error(f"Upsert subjects error: {res.error}")

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
                                # We clear existing ones for these ku_ids to prevent dupes, then insert
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

                    # Safety cap for full crawl
                    if not subject_type and total_subjects > 20000:
                        break

            # ── Phase 1.5: Build Mapping ──
            # Fetch all wanikani_id -> ku_id mappings for Phase 2 & 3
            ku_res = self.client.table("knowledge_units").select("wanikani_id, ku_id").execute()
            wk_id_to_ku_id = {row["wanikani_id"]: row["ku_id"] for row in ku_res.data}

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
                    subject_id = d.get("subject_id")
                    ku_id = wk_id_to_ku_id.get(subject_id)
                    
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
                    res = self.client.table("user_learning_states").upsert(
                        records, on_conflict="user_id,ku_id"
                    ).execute()
                    if hasattr(res, "error") and res.error:
                        logger.error(f"Upsert assignments error: {res.error}")

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
                    subject_id = d.get("subject_id")
                    ku_id = wk_id_to_ku_id.get(subject_id)
                    
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
                    res = self.client.table("user_review_statistics").upsert(
                        records, on_conflict="user_id,ku_id"
                    ).execute()
                    if hasattr(res, "error") and res.error:
                        logger.error(f"Upsert review_statistics error: {res.error}")

                total_stats += len(result.get("data", []))
                url = result.get("pages", {}).get("next_url")

            # ── Phase 4: Update user level from WaniKani ──
            try:
                user_resp = await http.get(f"{wanikani_base}/user", headers=headers)
                user_resp.raise_for_status()
                wk_user = user_resp.json()
                wk_level = wk_user.get("data", {}).get("level", 1)
                self.client.table("users").update({"level": wk_level}).eq("id", self.user_id).execute()
            except Exception as e:
                logger.warning(f"Could not sync user level: {e}")

        return {
            "success": True,
            "subjects_synced": total_subjects,
            "assignments_synced": total_assignments,
            "review_statistics_synced": total_stats,
        }
