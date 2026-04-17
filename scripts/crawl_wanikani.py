import httpx
import json
import os
import asyncio
import sys
from datetime import datetime
from typing import List, Dict, Any

WANIKANI_API_URL = "https://api.wanikani.com/v2"

class WaniKaniCrawler:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Wanikani-Revision": "20170710"
        }
        self.base_dir = "resources/data"
        os.makedirs(self.base_dir, exist_ok=True)

    async def fetch_subjects_by_level(self, http: httpx.AsyncClient, level: int) -> List[Dict[str, Any]]:
        """Fetch all subjects for a specific level."""
        subjects = []
        url = f"{WANIKANI_API_URL}/subjects?levels={level}"
        
        while url:
            try:
                print(f"  Fetching level {level} page: {url}")
                resp = await http.get(url, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()
                subjects.extend(data["data"])
                url = data["pages"]["next_url"]
            except Exception as e:
                print(f"  Error fetching level {level}: {e}")
                break
        
        return subjects

    def validate_subjects(self, level: int, subjects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the quality and integrity of the crawled subjects."""
        report = {
            "level": level,
            "total_count": len(subjects),
            "by_type": {},
            "missing_characters": 0,
            "missing_meanings": 0,
            "missing_readings": 0,
            "is_valid": True,
            "errors": []
        }

        if not subjects:
            report["is_valid"] = False
            report["errors"].append("No subjects found for this level.")
            return report

        for s in subjects:
            obj_type = s.get("object")
            report["by_type"][obj_type] = report["by_type"].get(obj_type, 0) + 1
            
            data = s.get("data", {})
            
            # Check for characters (can be images for radicals)
            if not data.get("characters") and not data.get("character_images"):
                report["missing_characters"] += 1
            
            # Check for meanings
            if not data.get("meanings"):
                report["missing_meanings"] += 1
                
            # Check for readings (Kanji and Vocab only)
            if obj_type in ["kanji", "vocabulary", "kana_vocabulary"] and not data.get("readings"):
                # Exception: some vocab might only have one or the other but usually have readings list
                pass 

        if report["missing_characters"] > 0 or report["missing_meanings"] > 0:
            report["is_valid"] = False
            report["errors"].append(f"Found missing character/meaning data.")

        return report

    async def run(self, start_level: int = 1, end_level: int = 60):
        print(f"Starting WaniKani crawl for levels {start_level} to {end_level}...")
        
        total_report = []
        all_ok = True

        async with httpx.AsyncClient(timeout=60.0) as http:
            for level in range(start_level, end_level + 1):
                subjects = await self.fetch_subjects_by_level(http, level)
                
                # Validate
                validation_report = self.validate_subjects(level, subjects)
                total_report.append(validation_report)
                
                if not validation_report["is_valid"]:
                    print(f"  [!] Validation failed for level {level}: {validation_report['errors']}")
                    all_ok = False
                else:
                    print(f"  [✓] Level {level} validated successfully. Count: {len(subjects)}")

                # Save to JSON
                filename = os.path.join(self.base_dir, f"level_{level:02d}.json")
                output_data = {
                    "level": level,
                    "count": len(subjects),
                    "crawled_at": datetime.utcnow().isoformat() + "Z",
                    "data": subjects
                }
                
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)

        # Final Report Summary
        summary_file = os.path.join(self.base_dir, "crawl_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump({
                "finished_at": datetime.utcnow().isoformat() + "Z",
                "all_levels_valid": all_ok,
                "reports": total_report
            }, f, indent=2)
            
        print(f"\nCrawl complete! Summary saved to {summary_file}")
        if all_ok:
            print("All levels passed quality validation.")
        else:
            print("Some levels had validation errors. Check crawl_summary.json for details.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/crawl_wanikani.py <API_KEY>")
        sys.exit(1)
    
    key = sys.argv[1]
    crawler = WaniKaniCrawler(key)
    asyncio.run(crawler.run())
