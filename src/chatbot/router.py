from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from typing import Annotated

from ..db import get_db, Cur
from .. import queries
from .bot_logic import ExpenseBotLogic

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])
bot_logic = ExpenseBotLogic()


@router.post("/send")
async def send_message(
    req: Request,
    cur: Annotated[Cur, Depends(get_db)]
):
    """Handle incoming chat messages"""
    data = await req.json()
    username = data.get("userId")  # This is actually username
    message = data.get("message", "").strip()
    
    if not username or not message:
        return JSONResponse(
            {"error": "userId and message are required"},
            status_code=400
        )
    
    # Save user message
    await cur.execute(queries.SAVE_CHAT_MESSAGE, (username, "user", message))
    
    # Get recent chat history for context
    await cur.execute(queries.GET_CHAT_HISTORY, (username, 10))
    history = await cur.fetchall()
    
    # Generate bot reply
    bot_response = await bot_logic.generate_reply(message, username, history)
    
    # Save bot message
    await cur.execute(queries.SAVE_CHAT_MESSAGE, (username, "bot", bot_response["reply"]))
    
    # Save extracted information
    for item in bot_response.get("extracted", []):
        await cur.execute(
            queries.SAVE_EXTRACTED_INFO,
            (username, item["category"], item["value"], item.get("context", ""))
        )
    
    await cur._connection.commit()
    
    return JSONResponse({
        "reply": bot_response["reply"],
        "extracted": bot_response.get("extracted", [])
    })


@router.get("/history")
async def get_history(
    userId: str,  # This is actually username
    cur: Annotated[Cur, Depends(get_db)]
):
    """Get chat history for user"""
    await cur.execute(queries.GET_CHAT_HISTORY, (userId, 50))
    messages = await cur.fetchall()
    
    return JSONResponse([
        {
            "sender": msg["sender"],
            "message": msg["message"],
            "timestamp": msg["timestamp"].isoformat() if msg["timestamp"] else None
        }
        for msg in messages
    ])


@router.get("/extracted")
async def get_extracted_info(
    userId: str,  # This is actually username
    cur: Annotated[Cur, Depends(get_db)]
):
    """Get extracted information that hasn't been used yet"""
    await cur.execute(queries.GET_EXTRACTED_INFO, (userId,))
    extracted = await cur.fetchall()
    
    return JSONResponse([
        {
            "category": item["category"],
            "value": item["value"],
            "context": item["context"],
            "timestamp": item["timestamp"].isoformat() if item.get("timestamp") else None
        }
        for item in extracted
    ])