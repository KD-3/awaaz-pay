import logging

from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.agent_api import router as agent_router
from app.config import settings
from app.db import init_db
from app.rail.mock_rail import router as rail_router
from app.seed import seed
from app.telephony.answer_xml import build_stream_answer_xml
from app.telephony.bridge import handle_stream_websocket

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AWAAZ-PAY")
app.include_router(rail_router)
app.include_router(agent_router)


@app.exception_handler(RequestValidationError)
async def log_validation_errors(request: Request, exc: RequestValidationError) -> JSONResponse:
    body = await request.body()
    logging.getLogger("awaazpay.main").warning(
        "422 on %s: body=%s errors=%s", request.url.path, body.decode("utf-8", "replace"), exc.errors()
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/answer")
@app.get("/answer")
async def answer(request: Request) -> Response:
    """Vobiz answer_url webhook - point the Application's Answer URL at
    <ngrok-url>/answer. Returns the Stream XML connecting the call to /stream."""
    base = settings.public_base_url.rstrip("/") if settings.public_base_url else str(request.base_url).rstrip("/")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/stream"
    status_callback = base + "/stream-status"
    xml = build_stream_answer_xml(ws_url, status_callback_url=status_callback)
    return Response(content=xml, media_type="text/xml")


@app.post("/stream-status")
async def stream_status(request: Request) -> dict:
    body = await request.body()
    logging.getLogger("awaazpay.main").info("stream status callback: %s", body.decode("utf-8", "replace"))
    return {"ok": True}


@app.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    await handle_stream_websocket(ws)
