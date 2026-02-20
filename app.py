import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import uvicorn

GITEA_URL = "http://localhost:3000"
TIMEOUT = 60

app = FastAPI()

LOADING_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="5">
  <title>Gitea iniciando...</title>
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
  <h2>🐣 Gitea está iniciando...</h2>
  <p>Listo en unos segundos. La página se recargará automáticamente.</p>
</body>
</html>
"""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.api_route(
    "/{path:path}",
    methods=["GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS"]
)
async def proxy(request: Request, path: str):
    url = f"{GITEA_URL}/{path}"

    try:
        body = await request.body()

        # Headers a excluir del forward
        excluded_req = {"host", "content-length", "transfer-encoding", "connection"}

        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in excluded_req
        }

        # Inyectar headers de proxy para que Gitea sepa que viene de HTTPS
        client_host = request.client.host if request.client else "unknown"
        headers["X-Forwarded-For"]   = client_host
        headers["X-Real-IP"]         = client_host
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-Host"]  = "opceanai-git.hf.space"
        headers["Host"]              = "opceanai-git.hf.space"

        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=False,
        ) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )

        # Headers a excluir de la respuesta
        excluded_resp = {
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        }

        response_headers = {}
        for k, v in resp.headers.multi_items():
            if k.lower() in excluded_resp:
                continue
            # Reescribir cookies para que funcionen en HTTPS
            if k.lower() == "set-cookie":
                v = v.replace("Path=/", "Path=/")
                if "SameSite" not in v:
                    v += "; SameSite=None"
                if "Secure" not in v:
                    v += "; Secure"
                # httpx Response no soporta multi-header directo, usamos lista
            response_headers[k] = v

        response = Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=response_headers,
        )

        # Set-Cookie múltiples — FastAPI solo permite uno por header dict
        # Los inyectamos manualmente
        cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else []
        for cookie in cookies:
            if "SameSite" not in cookie:
                cookie += "; SameSite=None"
            if "Secure" not in cookie:
                cookie += "; Secure"
            response.raw_headers.append(
                (b"set-cookie", cookie.encode("latin-1"))
            )

        return response

    except httpx.ConnectError:
        return HTMLResponse(content=LOADING_PAGE, status_code=503)

    except Exception as e:
        return Response(content=f"Proxy error: {e}", status_code=502)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )