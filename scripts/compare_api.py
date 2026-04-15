import os
import sys
import json
import asyncio
import httpx
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app.services.hanachan_service import HanachanService

WK_API_KEY = "c64f8759-d793-4198-9c0f-d83541831778"
WK_BASE_URL = "https://api.wanikani.com/v2"

HEADERS = {
    "Authorization": f"Bearer {WK_API_KEY}",
    "Wanikani-Revision": "20170710"
}

def remove_dynamic_fields(data):
    """Recursively removes fields that naturally change between Hanachan and WaniKani (urls, dates)"""
    if isinstance(data, dict):
        clean = {}
        for k, v in data.items():
            if k in ["url", "data_updated_at", "created_at", "updated_at", "document_url", "profile_url", "next_reviews_at"]:
                continue
            clean[k] = remove_dynamic_fields(v)
        return clean
    elif isinstance(data, list):
        return [remove_dynamic_fields(i) for i in data]
    return data

async def compare_endpoint(endpoint_name, ht_fetch, wk_fetch):
    print(f"\n--- Comparing {endpoint_name} ---")
    try:
        ht_data = await ht_fetch()
        wk_data = await wk_fetch()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    ht_clean = remove_dynamic_fields(ht_data)
    wk_clean = remove_dynamic_fields(wk_data)
    
    # Some structural matching (list sorting etc.)
    if str(ht_clean) == str(wk_clean):
         print(f"✅ {endpoint_name} Matches Perfectly!")
    else:
         print(f"❌ {endpoint_name} Mismatch Found!")
         print("\nHanachan Sample:")
         print(json.dumps(ht_clean, indent=2)[:800])
         print("\nWaniKani Sample:")
         print(json.dumps(wk_clean, indent=2)[:800])

async def main():
    print("1. Synchronizing user data from WaniKani to Hanachan DB...")
    mock_uuid = "00000000-0000-0000-0000-000000000001"
    
    service = HanachanService(user_id=mock_uuid)
    # Ensure mock user exists in DB to satisfy Foreign Key constraints
    service.client.table("users").upsert({
        "id": mock_uuid,
        "username": "tester",
        "email": "tester@example.com",
        "password_hash": "dummy"
    }).execute()
    
    # sync_wanikani is slow and might hang if network is unstable, disabling for getter test
    # await service.sync_wanikani(api_key=WK_API_KEY, subject_type='radical')
    
    print("\n2. Firing Parallel Queries")
    
    async with httpx.AsyncClient() as client:
        # /user Endpoint
        async def wk_user():
            r = await client.get(f"{WK_BASE_URL}/user", headers=HEADERS)
            return r.json()
            
        await compare_endpoint("/user", service.get_user, wk_user)
        
        # /summary Endpoint
        async def wk_summary():
            r = await client.get(f"{WK_BASE_URL}/summary", headers=HEADERS)
            return r.json()
            
        await compare_endpoint("/summary", service.get_summary, wk_summary)

        # /subjects Endpoint
        async def ht_subjects():
            res = await service.get_subjects()
            # limit strictly to 2 to compare
            res['data'] = res.get('data', [])[:2]
            return res

        async def wk_subjects():
            r = await client.get(f"{WK_BASE_URL}/subjects?types=radical&limit=2", headers=HEADERS)
            return r.json()

        await compare_endpoint("/subjects", ht_subjects, wk_subjects)

        # /assignments Endpoint
        async def ht_assignments():
            res = await service.get_assignments()
            res['data'] = res.get('data', [])[:2]
            return res

        async def wk_assignments():
            r = await client.get(f"{WK_BASE_URL}/assignments?limit=2", headers=HEADERS)
            return r.json()

        await compare_endpoint("/assignments", ht_assignments, wk_assignments)

if __name__ == "__main__":
    asyncio.run(main())
