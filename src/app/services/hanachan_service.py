from typing import Optional, List
from datetime import datetime
import json
import uuid
from app.db import get_db_connection


class HanachanService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_url = "/v2"

    def _row_to_dict(self, cursor, row):
        """Convert row to dict using cursor description"""
        if row is None:
            return None
        return dict(zip([col[0] for col in cursor.description], row))

    def _json_loads(self, val):
        """Safely load JSON"""
        if val is None:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return json.loads(val)
        return []

    async def get_user(self) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = %s", (self.user_id,))
            row = cursor.fetchone()
            
            if row:
                user = self._row_to_dict(cursor, row)
                return {
                    "object": "user",
                    "url": f"{self.base_url}/user",
                    "data_updated_at": user.get("updated_at"),
                    "data": {
                        "id": str(user["id"]),
                        "level": user.get("level", 1),
                        "username": user.get("username", "user"),
                        "started_at": user.get("created_at"),
                        "profile_url": f"https://hanachan.local/users/{user['id']}",
                        "subscription": {
                            "active": user.get("subscription_type") != "free",
                            "max_level_granted": user.get("max_level_granted", 60),
                            "type": user.get("subscription_type", "free"),
                            "period_ends_at": user.get("subscription_ends_at")
                        }
                    }
                }
            
            return {
                "object": "user",
                "url": f"{self.base_url}/user",
                "data_updated_at": datetime.utcnow().isoformat(),
                "data": {
                    "id": str(self.user_id),
                    "level": 1,
                    "username": "newuser",
                    "started_at": None,
                    "profile_url": f"https://hanachan.local/users/{self.user_id}",
                    "subscription": {
                        "active": False,
                        "max_level_granted": 3,
                        "type": "free",
                        "period_ends_at": None
                    }
                }
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM assignments WHERE user_id = %s"
            params = [self.user_id]
            
            if available_after:
                query += " AND available_at >= %s"
                params.append(available_after.isoformat())
            if available_before:
                query += " AND available_at <= %s"
                params.append(available_before.isoformat())
            if burned is not None:
                if burned:
                    query += " AND burned_at IS NOT NULL"
                else:
                    query += " AND burned_at IS NULL"
            if hidden is not None:
                query += " AND hidden = %s"
                params.append(hidden)
            if ids:
                query += f" AND id = ANY({','.join(['%s'] * len(ids))})"
                params.extend(ids)
            if immediately_available_for_lessons:
                query += " AND srs_stage = 0 AND unlocked_at IS NOT NULL"
            if immediately_available_for_review:
                query += " AND srs_stage > 0 AND available_at <= NOW() AND started_at IS NULL"
            if in_review:
                query += " AND started_at IS NOT NULL AND burned_at IS NULL"
            if levels:
                query += f" AND level = ANY({','.join(['%s'] * len(levels))})"
                params.extend(levels)
            if srs_stages:
                query += f" AND srs_stage = ANY({','.join(['%s'] * len(srs_stages))})"
                params.extend(srs_stages)
            if started is not None:
                if started:
                    query += " AND started_at IS NOT NULL"
                else:
                    query += " AND started_at IS NULL"
            if subject_ids:
                query += f" AND subject_id = ANY({','.join(['%s'] * len(subject_ids))})"
                params.extend(subject_ids)
            if subject_types:
                query += f" AND subject_type = ANY({','.join(['%s'] * len(subject_types))})"
                params.extend(subject_types)
            if unlocked is not None:
                if unlocked:
                    query += " AND unlocked_at IS NOT NULL"
                else:
                    query += " AND unlocked_at IS NULL"
            if updated_after:
                query += " AND updated_at >= %s"
                params.append(updated_after.isoformat())
            
            query += " ORDER BY created_at ASC LIMIT 500"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                data.append({
                    "id": item["id"],
                    "object": "assignment",
                    "url": f"{self.base_url}/assignments/{item['id']}",
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        "available_at": item.get("available_at"),
                        "burned_at": item.get("burned_at"),
                        "created_at": item.get("created_at"),
                        "hidden": item.get("hidden", False),
                        "passed_at": item.get("passed_at"),
                        "resurrected_at": item.get("resurrected_at"),
                        "srs_stage": item.get("srs_stage", 0),
                        "started_at": item.get("started_at"),
                        "subject_id": item["subject_id"],
                        "subject_type": item["subject_type"],
                        "unlocked_at": item.get("unlocked_at")
                    }
                })
            
            return {
                "object": "collection",
                "url": f"{self.base_url}/assignments",
                "data_updated_at": datetime.utcnow().isoformat(),
                "data": data,
                "pages": {"next_url": None, "previous_url": None, "per_page": 500},
                "total_count": len(data)
            }

    async def get_assignment(self, assignment_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assignments WHERE id = %s AND user_id = %s", (assignment_id, self.user_id))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Assignment not found")
            
            item = self._row_to_dict(cursor, row)
            return {
                "id": item["id"],
                "object": "assignment",
                "url": f"{self.base_url}/assignments/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "available_at": item.get("available_at"),
                    "burned_at": item.get("burned_at"),
                    "created_at": item.get("created_at"),
                    "hidden": item.get("hidden", False),
                    "passed_at": item.get("passed_at"),
                    "resurrected_at": item.get("resurrected_at"),
                    "srs_stage": item.get("srs_stage", 0),
                    "started_at": item.get("started_at"),
                    "subject_id": item["subject_id"],
                    "subject_type": item["subject_type"],
                    "unlocked_at": item.get("unlocked_at")
                }
            }

    async def start_assignment(self, assignment_id: int, started_at: Optional[datetime] = None) -> dict:
        start_time = started_at or datetime.utcnow()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE assignments SET started_at = %s, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
                (start_time.isoformat(), assignment_id, self.user_id)
            )
            conn.commit()
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Assignment not found")
            
            item = self._row_to_dict(cursor, row)
            return {
                "id": item["id"],
                "object": "assignment",
                "url": f"{self.base_url}/assignments/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "available_at": item.get("available_at"),
                    "burned_at": item.get("burned_at"),
                    "created_at": item.get("created_at"),
                    "hidden": item.get("hidden", False),
                    "passed_at": item.get("passed_at"),
                    "resurrected_at": item.get("resurrected_at"),
                    "srs_stage": item.get("srs_stage", 0),
                    "started_at": item.get("started_at"),
                    "subject_id": item["subject_id"],
                    "subject_type": item["subject_type"],
                    "unlocked_at": item.get("unlocked_at")
                }
            }

    async def get_level_progressions(
        self,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
    ) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM level_progressions WHERE user_id = %s"
            params = [self.user_id]
            
            if ids:
                query += f" AND id = ANY({','.join(['%s'] * len(ids))})"
                params.extend(ids)
            if updated_after:
                query += " AND updated_at >= %s"
                params.append(updated_after.isoformat())
            
            query += " ORDER BY created_at ASC LIMIT 500"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                data.append({
                    "id": item["id"],
                    "object": "level_progression",
                    "url": f"{self.base_url}/level_progressions/{item['id']}",
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        "level": item["level"],
                        "created_at": item.get("created_at"),
                        "unlocked_at": item.get("unlocked_at"),
                        "started_at": item.get("started_at"),
                        "passed_at": item.get("passed_at"),
                        "completed_at": item.get("completed_at"),
                        "abandoned_at": item.get("abandoned_at")
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

    async def get_level_progression(self, progression_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM level_progressions WHERE id = %s AND user_id = %s", (progression_id, self.user_id))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Level progression not found")
            
            item = self._row_to_dict(cursor, row)
            return {
                "id": item["id"],
                "object": "level_progression",
                "url": f"{self.base_url}/level_progressions/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "level": item["level"],
                    "created_at": item.get("created_at"),
                    "unlocked_at": item.get("unlocked_at"),
                    "started_at": item.get("started_at"),
                    "passed_at": item.get("passed_at"),
                    "completed_at": item.get("completed_at"),
                    "abandoned_at": item.get("abandoned_at")
                }
            }

    async def get_resets(
        self,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
    ) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM resets WHERE user_id = %s"
            params = [self.user_id]
            
            if ids:
                query += f" AND id = ANY({','.join(['%s'] * len(ids))})"
                params.extend(ids)
            if updated_after:
                query += " AND updated_at >= %s"
                params.append(updated_after.isoformat())
            
            query += " ORDER BY created_at ASC LIMIT 500"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                data.append({
                    "id": item["id"],
                    "object": "reset",
                    "url": f"{self.base_url}/resets/{item['id']}",
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        "created_at": item.get("created_at"),
                        "original_level": item["original_level"],
                        "target_level": item["target_level"],
                        "confirmed_at": item.get("confirmed_at")
                    }
                })
            
            return {
                "object": "collection",
                "url": f"{self.base_url}/resets",
                "data_updated_at": datetime.utcnow().isoformat(),
                "data": data,
                "pages": {"next_url": None, "previous_url": None, "per_page": 500},
                "total_count": len(data)
            }

    async def get_reset(self, reset_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resets WHERE id = %s AND user_id = %s", (reset_id, self.user_id))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Reset not found")
            
            item = self._row_to_dict(cursor, row)
            return {
                "id": item["id"],
                "object": "reset",
                "url": f"{self.base_url}/resets/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "created_at": item.get("created_at"),
                    "original_level": item["original_level"],
                    "target_level": item["target_level"],
                    "confirmed_at": item.get("confirmed_at")
                }
            }

    async def get_reviews(
        self,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
        assignment_ids: Optional[List[int]] = None,
        subject_ids: Optional[List[int]] = None,
    ) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM reviews WHERE user_id = %s"
            params = [self.user_id]
            
            if ids:
                query += f" AND id = ANY({','.join(['%s'] * len(ids))})"
                params.extend(ids)
            if updated_after:
                query += " AND updated_at >= %s"
                params.append(updated_after.isoformat())
            if assignment_ids:
                query += f" AND assignment_id = ANY({','.join(['%s'] * len(assignment_ids))})"
                params.extend(assignment_ids)
            if subject_ids:
                query += f" AND subject_id = ANY({','.join(['%s'] * len(subject_ids))})"
                params.extend(subject_ids)
            
            query += " ORDER BY created_at ASC LIMIT 500"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                data.append({
                    "id": item["id"],
                    "object": "review",
                    "url": f"{self.base_url}/reviews/{item['id']}",
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        "created_at": item.get("created_at"),
                        "assignment_id": item["assignment_id"],
                        "spaced_repetition_system_id": item["spaced_repetition_system_id"],
                        "subject_id": item["subject_id"],
                        "starting_srs_stage": item["starting_srs_stage"],
                        "ending_srs_stage": item["ending_srs_stage"],
                        "incorrect_meaning_answers": item["incorrect_meaning_answers"],
                        "incorrect_reading_answers": item["incorrect_reading_answers"]
                    }
                })
            
            return {
                "object": "collection",
                "url": f"{self.base_url}/reviews",
                "data_updated_at": datetime.utcnow().isoformat(),
                "data": data,
                "pages": {"next_url": None, "previous_url": None, "per_page": 500},
                "total_count": len(data)
            }

    async def create_review(
        self,
        assignment_id: int,
        incorrect_meaning_answers: int,
        incorrect_reading_answers: int,
        created_at: Optional[datetime] = None
    ) -> dict:
        review_time = created_at or datetime.utcnow()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get assignment
            cursor.execute("SELECT * FROM assignments WHERE id = %s AND user_id = %s", (assignment_id, self.user_id))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Assignment not found")
            assignment = self._row_to_dict(cursor, row)
            
            starting_srs_stage = assignment.get("srs_stage", 0)
            ending_srs_stage = starting_srs_stage
            
            if incorrect_meaning_answers == 0 and incorrect_reading_answers == 0:
                ending_srs_stage = min(starting_srs_stage + 1, 9)
            elif starting_srs_stage > 0:
                ending_srs_stage = max(starting_srs_stage - 1, 0)
            
            # Get SRS
            cursor.execute("SELECT * FROM spaced_repetition_systems WHERE id = 1")
            row = cursor.fetchone()
            srs = self._row_to_dict(cursor, row) if row else {"id": 1}
            
            # Insert review
            cursor.execute("""
                INSERT INTO reviews (user_id, assignment_id, spaced_repetition_system_id, subject_id, 
                    starting_srs_stage, ending_srs_stage, incorrect_meaning_answers, incorrect_reading_answers, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (self.user_id, assignment_id, srs["id"], assignment["subject_id"], 
                  starting_srs_stage, ending_srs_stage, incorrect_meaning_answers, incorrect_reading_answers, review_time.isoformat()))
            review = self._row_to_dict(cursor, cursor.fetchone())
            conn.commit()
            
            # Update assignment
            import math
            available_interval = ending_srs_stage * 24 * 3600
            available_at = datetime.fromtimestamp(review_time.timestamp() + available_interval)
            
            cursor.execute("""
                UPDATE assignments SET srs_stage = %s, available_at = %s, updated_at = NOW() 
                WHERE id = %s
            """, (ending_srs_stage, available_at.isoformat(), assignment_id))
            conn.commit()
            
            # Update review statistics
            cursor.execute("SELECT * FROM review_statistics WHERE subject_id = %s AND user_id = %s", 
                         (assignment["subject_id"], self.user_id))
            row = cursor.fetchone()
            if row:
                stat = self._row_to_dict(cursor, row)
                new_meaning_correct = stat.get("meaning_correct", 0) + (1 if incorrect_meaning_answers == 0 else 0)
                new_meaning_incorrect = stat.get("meaning_incorrect", 0) + (1 if incorrect_meaning_answers > 0 else 0)
                new_reading_correct = stat.get("reading_correct", 0) + (1 if incorrect_reading_answers == 0 else 0)
                new_reading_incorrect = stat.get("reading_incorrect", 0) + (1 if incorrect_reading_answers > 0 else 0)
                total = new_meaning_correct + new_meaning_incorrect + new_reading_correct + new_reading_incorrect
                percentage = (new_meaning_correct + new_reading_correct) / total * 100 if total > 0 else 0
                
                cursor.execute("""
                    UPDATE review_statistics SET 
                        meaning_correct = %s, meaning_incorrect = %s, reading_correct = %s, reading_incorrect = %s,
                        percentage_correct = %s, updated_at = NOW()
                    WHERE id = %s
                """, (new_meaning_correct, new_meaning_incorrect, new_reading_correct, new_reading_incorrect, percentage, stat["id"]))
                conn.commit()
                stat_id = stat["id"]
                stat_data = stat
            else:
                stat_id = None
                stat_data = {}
            
            return {
                "id": review["id"],
                "object": "review",
                "url": f"{self.base_url}/reviews/{review['id']}",
                "data_updated_at": review.get("updated_at"),
                "data": {
                    "created_at": review.get("created_at"),
                    "assignment_id": review["assignment_id"],
                    "spaced_repetition_system_id": review["spaced_repetition_system_id"],
                    "subject_id": review["subject_id"],
                    "starting_srs_stage": review["starting_srs_stage"],
                    "ending_srs_stage": review["ending_srs_stage"],
                    "incorrect_meaning_answers": review["incorrect_meaning_answers"],
                    "incorrect_reading_answers": review["incorrect_reading_answers"]
                },
                "resources_updated": {
                    "assignment": assignment,
                    "review_statistic": {"id": stat_id, "data": stat_data}
                }
            }

    async def get_review(self, review_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reviews WHERE id = %s AND user_id = %s", (review_id, self.user_id))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Review not found")
            
            item = self._row_to_dict(cursor, row)
            return {
                "id": item["id"],
                "object": "review",
                "url": f"{self.base_url}/reviews/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "created_at": item.get("created_at"),
                    "assignment_id": item["assignment_id"],
                    "spaced_repetition_system_id": item["spaced_repetition_system_id"],
                    "subject_id": item["subject_id"],
                    "starting_srs_stage": item["starting_srs_stage"],
                    "ending_srs_stage": item["ending_srs_stage"],
                    "incorrect_meaning_answers": item["incorrect_meaning_answers"],
                    "incorrect_reading_answers": item["incorrect_reading_answers"]
                }
            }

    async def get_review_statistics(
        self,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
        hidden: Optional[bool] = None,
        subject_ids: Optional[List[int]] = None,
        subject_types: Optional[List[str]] = None,
        percentages_greater_than: Optional[int] = None,
        percentages_less_than: Optional[int] = None,
    ) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM review_statistics WHERE user_id = %s"
            params = [self.user_id]
            
            if ids:
                query += f" AND id = ANY({','.join(['%s'] * len(ids))})"
                params.extend(ids)
            if updated_after:
                query += " AND updated_at >= %s"
                params.append(updated_after.isoformat())
            if hidden is not None:
                query += " AND hidden = %s"
                params.append(hidden)
            if subject_ids:
                query += f" AND subject_id = ANY({','.join(['%s'] * len(subject_ids))})"
                params.extend(subject_ids)
            if subject_types:
                query += f" AND subject_type = ANY({','.join(['%s'] * len(subject_types))})"
                params.extend(subject_types)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                percentage = item.get("percentage_correct", 0)
                
                if percentages_greater_than is not None and percentage <= percentages_greater_than:
                    continue
                if percentages_less_than is not None and percentage >= percentages_less_than:
                    continue
                
                data.append({
                    "id": item["id"],
                    "object": "review_statistic",
                    "url": f"{self.base_url}/review_statistics/{item['id']}",
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        "created_at": item.get("created_at"),
                        "hidden": item.get("hidden", False),
                        "meaning_correct": item.get("meaning_correct", 0),
                        "meaning_current_streak": item.get("meaning_current_streak", 0),
                        "meaning_incorrect": item.get("meaning_incorrect", 0),
                        "meaning_max_streak": item.get("meaning_max_streak", 0),
                        "reading_correct": item.get("reading_correct", 0),
                        "reading_current_streak": item.get("reading_current_streak", 0),
                        "reading_incorrect": item.get("reading_incorrect", 0),
                        "reading_max_streak": item.get("reading_max_streak", 0),
                        "percentage_correct": percentage,
                        "subject_id": item["subject_id"],
                        "subject_type": item["subject_type"]
                    }
                })
            
            return {
                "object": "collection",
                "url": f"{self.base_url}/review_statistics",
                "data_updated_at": datetime.utcnow().isoformat(),
                "data": data,
                "pages": {"next_url": None, "previous_url": None, "per_page": 500},
                "total_count": len(data)
            }

    async def get_review_statistic(self, statistic_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM review_statistics WHERE id = %s AND user_id = %s", (statistic_id, self.user_id))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Review statistic not found")
            
            item = self._row_to_dict(cursor, row)
            return {
                "id": item["id"],
                "object": "review_statistic",
                "url": f"{self.base_url}/review_statistics/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "created_at": item.get("created_at"),
                    "hidden": item.get("hidden", False),
                    "meaning_correct": item.get("meaning_correct", 0),
                    "meaning_current_streak": item.get("meaning_current_streak", 0),
                    "meaning_incorrect": item.get("meaning_incorrect", 0),
                    "meaning_max_streak": item.get("meaning_max_streak", 0),
                    "reading_correct": item.get("reading_correct", 0),
                    "reading_current_streak": item.get("reading_current_streak", 0),
                    "reading_incorrect": item.get("reading_incorrect", 0),
                    "reading_max_streak": item.get("reading_max_streak", 0),
                    "percentage_correct": item.get("percentage_correct", 0),
                    "subject_id": item["subject_id"],
                    "subject_type": item["subject_type"]
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM spaced_repetition_systems WHERE id > 0"
            
            if ids:
                query += f" AND id = ANY({','.join(['%s'] * len(ids))})"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                stages = self._json_loads(item.get("stages"))
                
                data.append({
                    "id": item["id"],
                    "object": "spaced_repetition_system",
                    "url": f"{self.base_url}/spaced_repetition_systems/{item['id']}",
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        "created_at": item.get("created_at"),
                        "name": item["name"],
                        "description": item.get("description", ""),
                        "unlocking_stage_position": item.get("unlocking_stage_position", 0),
                        "starting_stage_position": item.get("starting_stage_position", 1),
                        "passing_stage_position": item.get("passing_stage_position", 5),
                        "burning_stage_position": item.get("burning_stage_position", 9),
                        "stages": stages
                    }
                })
            
            return {
                "object": "collection",
                "url": f"{self.base_url}/spaced_repetition_systems",
                "data_updated_at": datetime.utcnow().isoformat(),
                "data": data,
                "pages": {"next_url": None, "previous_url": None, "per_page": 500},
                "total_count": len(data)
            }

    async def get_spaced_repetition_system(self, srs_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spaced_repetition_systems WHERE id = %s", (srs_id,))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Spaced repetition system not found")
            
            item = self._row_to_dict(cursor, row)
            stages = self._json_loads(item.get("stages"))
            
            return {
                "id": item["id"],
                "object": "spaced_repetition_system",
                "url": f"{self.base_url}/spaced_repetition_systems/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "created_at": item.get("created_at"),
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "unlocking_stage_position": item.get("unlocking_stage_position", 0),
                    "starting_stage_position": item.get("starting_stage_position", 1),
                    "passing_stage_position": item.get("passing_stage_position", 5),
                    "burning_stage_position": item.get("burning_stage_position", 9),
                    "stages": stages
                }
            }

    async def get_study_materials(
        self,
        ids: Optional[List[int]] = None,
        updated_after: Optional[datetime] = None,
    ) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM study_materials WHERE user_id = %s"
            params = [self.user_id]
            
            if ids:
                query += f" AND id = ANY({','.join(['%s'] * len(ids))})"
            if updated_after:
                query += " AND updated_at >= %s"
                params.append(updated_after.isoformat())
            
            query += " ORDER BY created_at ASC LIMIT 500"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                data.append({
                    "id": item["id"],
                    "object": "study_material",
                    "url": f"{self.base_url}/study_materials/{item['id']}",
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        "created_at": item.get("created_at"),
                        "hidden": item.get("hidden", False),
                        "meaning_note": item.get("meaning_note"),
                        "meaning_synonyms": item.get("meaning_synonyms", []),
                        "reading_note": item.get("reading_note"),
                        "subject_id": item["subject_id"],
                        "subject_type": item["subject_type"]
                    }
                })
            
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
        subject_id: int,
        meaning_note: Optional[str] = None,
        reading_note: Optional[str] = None,
        meaning_synonyms: Optional[List[str]] = None
    ) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM subjects WHERE id = %s", (subject_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Subject not found")
            subject = self._row_to_dict(cursor, row)
            
            cursor.execute("""
                INSERT INTO study_materials (user_id, subject_id, subject_type, meaning_note, reading_note, meaning_synonyms)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (self.user_id, subject_id, subject.get("type", "vocabulary"), meaning_note, reading_note, meaning_synonyms or []))
            item = self._row_to_dict(cursor, cursor.fetchone())
            conn.commit()
            
            return {
                "id": item["id"],
                "object": "study_material",
                "url": f"{self.base_url}/study_materials/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "created_at": item.get("created_at"),
                    "hidden": item.get("hidden", False),
                    "meaning_note": item.get("meaning_note"),
                    "meaning_synonyms": item.get("meaning_synonyms", []),
                    "reading_note": item.get("reading_note"),
                    "subject_id": item["subject_id"],
                    "subject_type": item["subject_type"]
                }
            }

    async def get_study_material(self, material_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM study_materials WHERE id = %s AND user_id = %s", (material_id, self.user_id))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Study material not found")
            
            item = self._row_to_dict(cursor, row)
            return {
                "id": item["id"],
                "object": "study_material",
                "url": f"{self.base_url}/study_materials/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "created_at": item.get("created_at"),
                    "hidden": item.get("hidden", False),
                    "meaning_note": item.get("meaning_note"),
                    "meaning_synonyms": item.get("meaning_synonyms", []),
                    "reading_note": item.get("reading_note"),
                    "subject_id": item["subject_id"],
                    "subject_type": item["subject_type"]
                }
            }

    async def update_study_material(
        self,
        material_id: int,
        meaning_note: Optional[str] = None,
        reading_note: Optional[str] = None,
        meaning_synonyms: Optional[List[str]] = None
    ) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            
            if meaning_note is not None:
                updates.append("meaning_note = %s")
                params.append(meaning_note)
            if reading_note is not None:
                updates.append("reading_note = %s")
                params.append(reading_note)
            if meaning_synonyms is not None:
                updates.append("meaning_synonyms = %s")
                params.append(meaning_synonyms)
            
            if not updates:
                raise ValueError("No fields to update")
            
            params.append(material_id)
            params.append(self.user_id)
            
            query = f"UPDATE study_materials SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *"
            cursor.execute(query, params)
            item = self._row_to_dict(cursor, cursor.fetchone())
            conn.commit()
            
            if not item:
                raise ValueError("Study material not found")
            
            return {
                "id": item["id"],
                "object": "study_material",
                "url": f"{self.base_url}/study_materials/{item['id']}",
                "data_updated_at": item.get("updated_at"),
                "data": {
                    "created_at": item.get("created_at"),
                    "hidden": item.get("hidden", False),
                    "meaning_note": item.get("meaning_note"),
                    "meaning_synonyms": item.get("meaning_synonyms", []),
                    "reading_note": item.get("reading_note"),
                    "subject_id": item["subject_id"],
                    "subject_type": item["subject_type"]
                }
            }

    async def get_summary(self) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assignments WHERE user_id = %s", (self.user_id,))
            rows = cursor.fetchall()
            
            lessons = []
            reviews = []
            next_reviews_at = None
            
            for row in rows:
                item = self._row_to_dict(cursor, row)
                if item.get("srs_stage", 0) == 0 and item.get("unlocked_at") and not item.get("started_at"):
                    lessons.append({
                        "available_at": item.get("available_at"),
                        "subject_ids": [item["subject_id"]]
                    })
                
                if item.get("srs_stage", 0) > 0 and item.get("started_at") and not item.get("burned_at"):
                    available_at = item.get("available_at")
                    if available_at:
                        reviews.append({
                            "available_at": available_at,
                            "subject_ids": [item["subject_id"]]
                        })
                        if not next_reviews_at or str(available_at) < str(next_reviews_at):
                            next_reviews_at = available_at
            
            return {
                "object": "report",
                "url": f"{self.base_url}/summary",
                "data_updated_at": datetime.utcnow().isoformat(),
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM subjects WHERE user_id = %s"
            params = [self.user_id]
            
            if updated_after:
                query += " AND updated_at >= %s"
                params.append(updated_after.isoformat())
            
            query += " ORDER BY created_at ASC LIMIT 500"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                item = self._row_to_dict(cursor, row)
                subject_type = item.get("type", "vocabulary")
                url = f"{self.base_url}/subjects/{item['id']}"
                
                meanings = self._json_loads(item.get("meanings"))
                auxiliary_meanings = self._json_loads(item.get("auxiliary_meanings"))
                
                base_data = {
                    "auxiliary_meanings": auxiliary_meanings,
                    "characters": item.get("characters"),
                    "created_at": item.get("created_at"),
                    "document_url": item.get("document_url", ""),
                    "hidden_at": item.get("hidden_at"),
                    "lesson_position": item.get("lesson_position", 0),
                    "level": item.get("level", 1),
                    "meaning_mnemonic": item.get("meaning_mnemonic", ""),
                    "meanings": meanings,
                    "slug": item.get("slug", ""),
                    "spaced_repetition_system_id": item.get("spaced_repetition_system_id", 1)
                }
                
                if subject_type == "radical":
                    data.append({
                        "id": item["id"],
                        "object": "radical",
                        "url": url,
                        "data_updated_at": item.get("updated_at"),
                        "data": {
                            **base_data,
                            "amalgamation_subject_ids": item.get("amalgamation_subject_ids", []),
                            "character_images": self._json_loads(item.get("character_images"))
                        }
                    })
                elif subject_type == "kanji":
                    data.append({
                        "id": item["id"],
                        "object": "kanji",
                        "url": url,
                        "data_updated_at": item.get("updated_at"),
                        "data": {
                            **base_data,
                            "amalgamation_subject_ids": item.get("amalgamation_subject_ids", []),
                            "component_subject_ids": item.get("component_subject_ids", []),
                            "meaning_hint": item.get("meaning_hint"),
                            "reading_hint": item.get("reading_hint"),
                            "reading_mnemonic": item.get("reading_mnemonic", ""),
                            "readings": self._json_loads(item.get("readings")),
                            "visually_similar_subject_ids": item.get("visually_similar_subject_ids", [])
                        }
                    })
                else:
                    data.append({
                        "id": item["id"],
                        "object": subject_type,
                        "url": url,
                        "data_updated_at": item.get("updated_at"),
                        "data": {
                            **base_data,
                            "component_subject_ids": item.get("component_subject_ids", []),
                            "context_sentences": self._json_loads(item.get("context_sentences")),
                            "parts_of_speech": item.get("parts_of_speech", []),
                            "pronunciation_audios": self._json_loads(item.get("pronunciation_audios")),
                            "readings": self._json_loads(item.get("readings")),
                            "reading_mnemonic": item.get("reading_mnemonic", "")
                        }
                    })
            
            return {
                "object": "collection",
                "url": f"{self.base_url}/subjects",
                "data_updated_at": datetime.utcnow().isoformat(),
                "data": data,
                "pages": {"next_url": None, "previous_url": None, "per_page": 500},
                "total_count": len(data)
            }

    async def get_subject(self, subject_id: int) -> dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subjects WHERE id = %s", (subject_id,))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("Subject not found")
            
            item = self._row_to_dict(cursor, row)
            subject_type = item.get("type", "vocabulary")
            url = f"{self.base_url}/subjects/{item['id']}"
            
            meanings = self._json_loads(item.get("meanings"))
            auxiliary_meanings = self._json_loads(item.get("auxiliary_meanings"))
            
            base_data = {
                "auxiliary_meanings": auxiliary_meanings,
                "characters": item.get("characters"),
                "created_at": item.get("created_at"),
                "document_url": item.get("document_url", ""),
                "hidden_at": item.get("hidden_at"),
                "lesson_position": item.get("lesson_position", 0),
                "level": item.get("level", 1),
                "meaning_mnemonic": item.get("meaning_mnemonic", ""),
                "meanings": meanings,
                "slug": item.get("slug", ""),
                "spaced_repetition_system_id": item.get("spaced_repetition_system_id", 1)
            }
            
            if subject_type == "radical":
                return {
                    "id": item["id"],
                    "object": "radical",
                    "url": url,
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        **base_data,
                        "amalgamation_subject_ids": item.get("amalgamation_subject_ids", []),
                        "character_images": self._json_loads(item.get("character_images"))
                    }
                }
            elif subject_type == "kanji":
                return {
                    "id": item["id"],
                    "object": "kanji",
                    "url": url,
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        **base_data,
                        "amalgamation_subject_ids": item.get("amalgamation_subject_ids", []),
                        "component_subject_ids": item.get("component_subject_ids", []),
                        "meaning_hint": item.get("meaning_hint"),
                        "reading_hint": item.get("reading_hint"),
                        "reading_mnemonic": item.get("reading_mnemonic", ""),
                        "readings": self._json_loads(item.get("readings")),
                        "visually_similar_subject_ids": item.get("visually_similar_subject_ids", [])
                    }
                }
            else:
                return {
                    "id": item["id"],
                    "object": subject_type,
                    "url": url,
                    "data_updated_at": item.get("updated_at"),
                    "data": {
                        **base_data,
                        "component_subject_ids": item.get("component_subject_ids", []),
                        "context_sentences": self._json_loads(item.get("context_sentences")),
                        "parts_of_speech": item.get("parts_of_speech", []),
                        "pronunciation_audios": self._json_loads(item.get("pronunciation_audios")),
                        "readings": self._json_loads(item.get("readings")),
                        "reading_mnemonic": item.get("reading_mnemonic", "")
                    }
                }
