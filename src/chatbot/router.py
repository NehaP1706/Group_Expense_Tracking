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
    """Handle incoming chat messages with state management"""
    data = await req.json()
    username = data.get("userId")
    message = data.get("message", "").strip()
    
    if not username or not message:
        return JSONResponse(
            {"error": "userId and message are required"},
            status_code=400
        )
    
    try:
        # Save user message
        await cur.execute(queries.SAVE_CHAT_MESSAGE, (username, "user", message))
        
        # Get recent chat history for context
        await cur.execute(queries.GET_CHAT_HISTORY, (username, 10))
        history = await cur.fetchall()
        
        # Generate bot reply with state management (pass cursor)
        bot_response = await bot_logic.generate_reply(message, username, history, cur)
        
        # Save bot message
        await cur.execute(queries.SAVE_CHAT_MESSAGE, (username, "bot", bot_response["reply"]))
        
        # Save extracted information if any
        for item in bot_response.get("extracted", []):
            await cur.execute(
                queries.SAVE_EXTRACTED_INFO,
                (username, item.get("category", "unknown"), item.get("value", ""), item.get("context", ""))
            )
        
        await cur._connection.commit()
        
        response_data = {
            "reply": bot_response["reply"],
            "extracted": bot_response.get("extracted", [])
        }
        
        # If there's an action to perform
        if bot_response.get("action"):
            response_data["action"] = bot_response["action"]
            response_data["action_data"] = bot_response.get("data", {})
        
        return JSONResponse(response_data)
        
    except Exception as e:
        print(f"Error in chatbot send: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/history")
async def get_history(
    userId: str,
    cur: Annotated[Cur, Depends(get_db)]
):
    """Get chat history for user"""
    try:
        await cur.execute(queries.GET_CHAT_HISTORY, (userId, 50))
        messages = await cur.fetchall()
        
        return JSONResponse([
            {
                "sender": msg["sender"],
                "message": msg["message"],
                "timestamp": msg["timestamp"].isoformat() if msg.get("timestamp") else None
            }
            for msg in messages
        ])
    except Exception as e:
        print(f"Error getting history: {e}")
        return JSONResponse([], status_code=200)


@router.get("/state")
async def get_state(
    userId: str,
    cur: Annotated[Cur, Depends(get_db)]
):
    """Get user's current conversation state"""
    try:
        await cur.execute(
            "SELECT state, state_data FROM ChatbotState WHERE user_id = %s",
            (userId,)
        )
        state = await cur.fetchone()
        
        if state:
            return JSONResponse({
                "state": state["state"],
                "data": state["state_data"]
            })
        
        return JSONResponse({"state": "menu", "data": {}})
    except Exception as e:
        print(f"Error getting state: {e}")
        return JSONResponse({"state": "menu", "data": {}})


@router.post("/reset")
async def reset_state(
    req: Request,
    cur: Annotated[Cur, Depends(get_db)]
):
    """Reset user's conversation state to menu"""
    data = await req.json()
    user_id = data.get("userId")
    
    if not user_id:
        return JSONResponse({"error": "userId required"}, status_code=400)
    
    try:
        await cur.execute(
            """
            INSERT INTO ChatbotState (user_id, state, state_data) 
            VALUES (%s, 'menu', NULL)
            ON DUPLICATE KEY UPDATE state = 'menu', state_data = NULL
            """,
            (user_id,)
        )
        await cur._connection.commit()
        
        return JSONResponse({"message": "State reset to menu"})
    except Exception as e:
        print(f"Error resetting state: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/extracted")
async def get_extracted_info(
    userId: str,
    cur: Annotated[Cur, Depends(get_db)]
):
    """Get extracted information that hasn't been used yet"""
    try:
        await cur.execute(queries.GET_EXTRACTED_INFO, (userId,))
        extracted = await cur.fetchall()
        
        return JSONResponse([
            {
                "category": item["category"],
                "value": item["value"],
                "context": item.get("context", ""),
                "timestamp": item["timestamp"].isoformat() if item.get("timestamp") else None
            }
            for item in extracted
        ])
    except Exception as e:
        print(f"Error getting extracted info: {e}")
        return JSONResponse([], status_code=200)