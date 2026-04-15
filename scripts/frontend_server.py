import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn

app = FastAPI()

# Backend URL to proxy to
BACKEND_URL = "http://localhost:7000"

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dist_path = os.path.join(project_root, "kanjischool", "dist")

if not os.path.exists(dist_path):
    print(f"Error: {dist_path} does not exist. Build the frontend first.")
    # We won't exit here to allow manual build later
else:
    # Mount assets directory
    assets_path = os.path.join(dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

@app.api_route("/v2/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_v2(request: Request, path: str):
    """
    Reverse proxy WaniKani API calls to the Hanachan backend.
    """
    url = f"{BACKEND_URL}/v2/{path}"
    
    # Forward the query parameters
    params = dict(request.query_params)
    
    # Forward headers (excluding host)
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    
    # Get request body
    body = await request.body()
    
    async with httpx.AsyncClient() as client:
        try:
            # We use stream here to handle large responses efficiently if needed
            rp_resp = await client.request(
                method=request.method,
                url=url,
                params=params,
                headers=headers,
                content=body,
                follow_redirects=True,
                timeout=30.0
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

        # Return the response as-is
        # Some headers like content-encoding might need careful handling, 
        # but for simple API proxying this is usually fine.
        exclude_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        resp_headers = {k: v for k, v in rp_resp.headers.items() if k.lower() not in exclude_headers}
        
        return StreamingResponse(
            rp_resp.aiter_bytes(),
            status_code=rp_resp.status_code,
            headers=resp_headers
        )

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if not os.path.exists(dist_path):
        return {"message": "Frontend not built yet. Run 'bun run build' in kanjischool dir."}

    # If the file exists in dist, serve it
    file_path = os.path.join(dist_path, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Otherwise, SPA routing: serve index.html
    index_path = os.path.join(dist_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    raise HTTPException(status_code=404, detail="Page not found")

if __name__ == "__main__":
    print("Starting KanjiSchool Frontend Proxy Server on port 7100...")
    print(f"Proxying /v2 -> {BACKEND_URL}/v2")
    uvicorn.run(app, host="0.0.0.0", port=7100)
