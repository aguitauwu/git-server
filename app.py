import asyncio
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import uvicorn

FORGEJO_URL = "http://localhost:3000"
TIMEOUT = 30

app = FastAPI()

LOADING_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="5">
  <title>Forgejo iniciando...</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: sans-serif;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      height: 100vh;
      background: #0d1117; color: #eee;
    }
    .spinner {
      width: 52px; height: 52px;
      border: 5px solid #333;
      border-top-color: #ff7b72;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 20px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    h2 { font-size: 1.3rem; margin-bottom: 8px; }
    p  { color: #888; font-size: 0.85rem; }
  </style>
</head>
<body>
  <div class="spinner"></div>
  <h2>🐣 Forgejo está iniciando...</h2>
  <p>Listo en unos segundos. La página se recargará automáticamente.</p>
</body>
</html>
"""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/_debug/forgejo-status")
async def forgejo_status():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{FORGEJO_URL}/api/v1/version")
            return {"forgejo": resp.json()}
    except Exception as e:
        return {"error": str(e)}

@app.api_route(
    "/{path:path}",
    methods=["GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS"]
)
async def proxy(request: Request, path: str):
    url = f"{FORGEJO_URL}/{path}"

    try:
        body = await request.body()

        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length")
        }

        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=False
        ) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=request.query_params,
                cookies=request.cookies,
            )

        excluded = {
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        }
        response_headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() not in excluded
        }

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=response_headers,
        )

    except httpx.ConnectError:
        return HTMLResponse(content=LOADING_PAGE, status_code=503)

    except Exception as e:
        return Response(content=f"Proxy error: {e}", status_code=502)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="info")