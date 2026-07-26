"""Mocked payment rail (§12), exposed over HTTP for curl/judge probing. Never
wires a real payment rail. Business logic lives in rail_core.py so the
telephony bridge can call the same functions in-process."""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_connection
from app.rail.rail_core import PayeeNotFound, create_transfer, get_status, resolve_payee, settle_after_delay

router = APIRouter(prefix="/rail", tags=["rail"])


class ResolvePayeeRequest(BaseModel):
    caller_id: str
    payee_id: str


class ResolvePayeeResponse(BaseModel):
    payee_id: str
    name: str
    masked_account: str


class TransferRequest(BaseModel):
    caller_id: str
    payee_id: str
    amount_paise: int
    idempotency_key: str


class TransferResponse(BaseModel):
    txn_id: str
    status: str


class StatusResponse(BaseModel):
    txn_id: str
    status: str


@router.post("/resolve_payee", response_model=ResolvePayeeResponse)
def resolve_payee_endpoint(req: ResolvePayeeRequest) -> ResolvePayeeResponse:
    conn = get_connection()
    try:
        result = resolve_payee(conn, req.caller_id, req.payee_id)
    except PayeeNotFound:
        raise HTTPException(status_code=404, detail="payee not found for caller")
    finally:
        conn.close()
    return ResolvePayeeResponse(**result)


@router.post("/transfer", response_model=TransferResponse)
async def transfer_endpoint(req: TransferRequest) -> TransferResponse:
    conn = get_connection()
    try:
        txn_id, status = create_transfer(conn, req.caller_id, req.payee_id, req.amount_paise, req.idempotency_key)
        conn.commit()
    except PayeeNotFound:
        raise HTTPException(status_code=404, detail="payee not found for caller")
    finally:
        conn.close()

    if status == "pending":
        asyncio.create_task(settle_after_delay(get_connection, txn_id))
    return TransferResponse(txn_id=txn_id, status=status)


@router.get("/status/{txn_id}", response_model=StatusResponse)
def status_endpoint(txn_id: str) -> StatusResponse:
    conn = get_connection()
    try:
        status = get_status(conn, txn_id)
    finally:
        conn.close()
    if status is None:
        raise HTTPException(status_code=404, detail="txn not found")
    return StatusResponse(txn_id=txn_id, status=status)
