from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Annotated
from uuid import uuid4
from datetime import datetime
import os
from pathlib import Path

from .db import connect_to_db, get_db, Cur
from .config import get_config
from . import queries
from .chatbot.router import router as chatbot_router  # NEW


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await connect_to_db()
    yield
    if app.state.db:
        await app.state.db.close()


app = FastAPI(lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Create directories if they don't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs(str(BASE_DIR / "static"), exist_ok=True)  # NEW

# Mount static files and uploads
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), "static")  # NEW
app.mount("/uploads", StaticFiles(directory="uploads"), "uploads")

# Include chatbot router
app.include_router(chatbot_router)  # NEW


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(req: Request, exc: StarletteHTTPException):
    return templates.TemplateResponse(
        req,
        "error.html",
        {"status": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code
    )


# AUTHENTICATION ROUTES
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login")


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(req: Request):
    return templates.TemplateResponse(req, "signup.html", {})


@app.post("/signup")
async def signup(
    req: Request,
    cur: Annotated[Cur, Depends(get_db)],
    username: str = Form(...),   # NEW FIELD
    first_name: str = Form(...),
    last_name: str = Form(...),
    mobile: str = Form(...),
    currency: str = Form(...),
    password: str = Form(...)
):
    # Check if username exists
    await cur.execute(queries.GET_USER, (username,))
    if await cur.fetchone():
        return templates.TemplateResponse(req, "signup.html", {"error": "Username already taken"})

    # Insert with Username (No UUID generation needed)
    await cur.execute(queries.CREATE_USER, (username, first_name, last_name, mobile, currency, password))
    await cur._connection.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(req: Request):
    return templates.TemplateResponse(req, "login.html", {})

@app.post("/login")
async def login(
    req: Request,
    cur: Annotated[Cur, Depends(get_db)],
    username: str = Form(...), # Changed from first_name
    password: str = Form(...)
):
    await cur.execute(queries.GET_USER, (username,))
    user = await cur.fetchone()
    
    if not user or user["password"] != password:
        return templates.TemplateResponse(req, "login.html", {"error": "Invalid credentials"})
    
    # Redirect using username as the ID
    return RedirectResponse(url=f"/dashboard?userId={user['username']}", status_code=303)


# DASHBOARD
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(req: Request, userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_USER, (userId,)) # Updated query name
    user = await cur.fetchone()
    
    if not user:
        raise StarletteHTTPException(status_code=404, detail="User not found")
    
    return templates.TemplateResponse(req, "dashboard.html", {"user": user, "userId": userId})


# PROFILE
@app.get("/profile", response_class=HTMLResponse)
async def profile(req: Request, userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_USER, (userId,)) # Updated query name
    user = await cur.fetchone()
    
    if not user:
        raise StarletteHTTPException(status_code=404, detail="User not found")
    
    await cur.execute(queries.GET_GROUPS_FOR_USER, (userId,))
    groups = await cur.fetchall()
    
    await cur.execute(queries.GET_PAID_TRANSACTIONS_FOR_USER, (userId, userId))
    transactions = await cur.fetchall()
    
    return templates.TemplateResponse(
        req, "profile.html", 
        {"user": user, "userId": userId, "groups": groups, "transactions": transactions}
    )


# API ENDPOINTS FOR AJAX
@app.get("/api/profile")
async def api_profile(userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_USER, (userId,))
    user = await cur.fetchone()
    
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    
    user_dict = dict(user)
    
    if user_dict.get("debt") is not None:
        user_dict["debt"] = float(user_dict["debt"])
        
    return JSONResponse(user_dict)


@app.get("/api/transactions")
async def api_transactions(userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_PAID_TRANSACTIONS_FOR_USER, (userId, userId))
    transactions = await cur.fetchall()
    # FIX: Remove default=str
    return JSONResponse([
        {
            **dict(t),
            'payment_timestamp': t['payment_timestamp'].isoformat() if t.get('payment_timestamp') else None
        }
        for t in transactions
    ])


# GROUPS
@app.get("/groups", response_class=HTMLResponse)
async def groups(req: Request, userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_GROUPS_FOR_USER, (userId,))
    groups_data = await cur.fetchall()
    
    groups_with_details = []
    for group in groups_data:
        # Use simple key (group_name)
        await cur.execute(queries.GET_GROUP_MEMBERS, (group["group_name"],))
        members = await cur.fetchall()
        
        await cur.execute(queries.GET_EVENTS_FOR_GROUP, (group["group_name"],))
        events = await cur.fetchall()
        
        events_with_transactions = []
        for event in events:
            await cur.execute(queries.GET_TRANSACTIONS_FOR_EVENT, 
                              (group["group_name"], event["event_name"]))
            transactions = await cur.fetchall()
            event_dict = dict(event)
            event_dict["transactions"] = [dict(t) for t in transactions]
            events_with_transactions.append(event_dict)
        
        group_dict = dict(group)
        group_dict["members"] = [dict(m) for m in members]
        group_dict["events"] = events_with_transactions
        groups_with_details.append(group_dict)
    
    return templates.TemplateResponse(
        req, "groups.html", 
        {"groups": groups_with_details, "userId": userId}
    )


@app.get("/api/groupsForUser")
async def api_groups_for_user(userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_GROUPS_FOR_USER, (userId,))
    groups = await cur.fetchall()
    
    groups_with_details = []
    for group in groups:
        await cur.execute(queries.GET_GROUP_MEMBERS, (group["group_id"],))
        members = await cur.fetchall()
        
        await cur.execute(queries.GET_EVENTS_FOR_GROUP, (group["group_id"],))
        events = await cur.fetchall()
        
        events_with_transactions = []
        for event in events:
            await cur.execute(queries.GET_TRANSACTIONS_FOR_EVENT, (group["group_id"], event["event_name"]))
            transactions = await cur.fetchall()
            event_dict = dict(event)
            # Convert timestamps
            event_dict["created_at"] = event_dict["created_at"].isoformat() if event_dict.get("created_at") else None
            event_dict["transactions"] = [
                {
                    **dict(t),
                    'timestamp': t['timestamp'].isoformat() if t.get('timestamp') else None
                }
                for t in transactions
            ]
            events_with_transactions.append(event_dict)
        
        group_dict = dict(group)
        group_dict["created_at"] = group_dict["created_at"].isoformat() if group_dict.get("created_at") else None
        group_dict["members"] = [m["user_id"] for m in members]
        group_dict["events"] = events_with_transactions
        groups_with_details.append(group_dict)
    
    # FIX: Remove default=str
    return JSONResponse(groups_with_details)


@app.get("/make-group", response_class=HTMLResponse)
async def make_group_page(req: Request, userId: str):
    return templates.TemplateResponse(req, "make_group.html", {"userId": userId})


@app.post("/api/groups")
async def create_group(req: Request, cur: Annotated[Cur, Depends(get_db)]):
    data = await req.json()
    
    creator_id = data["createdBy"]
    group_name = data["groupName"]
    members_input = data.get("members", [])
    
    # 1. GLOBAL UNIQUENESS CHECK
    await cur.execute("SELECT * FROM `Group` WHERE group_name = %s", (group_name,))
    if await cur.fetchone():
        return JSONResponse(
            {"error": f"The group name '{group_name}' is already taken. Please choose another name."}, 
            status_code=400
        )

    # 2. Validate Users
    clean_members = list(set([m.strip() for m in members_input if m.strip()]))
    
    await cur.execute(queries.GET_USER, (creator_id,))
    if not await cur.fetchone():
        return JSONResponse({"error": "Creator account not found."}, status_code=400)

    for username in clean_members:
        if username == creator_id: continue
        await cur.execute(queries.GET_USER, (username,))
        if not await cur.fetchone():
             return JSONResponse({"error": f"User '{username}' does not exist."}, status_code=400)

    try:
        # 3. Create Group
        await cur.execute(
            queries.CREATE_GROUP, 
            (group_name, creator_id, data.get("duration", ""))
        )
        
        # 4. Add Members (Ensure creator is added)
        if creator_id not in clean_members:
            clean_members.append(creator_id)

        for member_id in clean_members:
            await cur.execute(queries.ADD_GROUP_MEMBER, (group_name, member_id))
        
        # 5. Add Initial Events
        if data.get("events"):
            for event in data["events"]:
                await cur.execute(
                    queries.CREATE_EVENT,
                    (group_name, event["eventName"], creator_id, event.get("description", ""), event.get("duration", ""))
                )
                
                for txn in event.get("transactions", []):
                    await cur.execute(
                        queries.CREATE_TRANSACTION,
                        (
                            group_name, event["eventName"], creator_id, 
                            txn["owedBy"], txn["owedTo"], txn["amount"], 
                            txn.get("reason", ""), datetime.now()
                        )
                    )
        
        await cur._connection.commit()
        return JSONResponse({"message": "Group created"})

    except Exception as e:
        await cur._connection.rollback()
        print(f"Error creating group: {e}")
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)


@app.post("/api/groups/addEvent")
async def add_event(req: Request, cur: Annotated[Cur, Depends(get_db)]):
    data = await req.json()
    event = data["event"]
    group_name = data["groupName"]
    current_user = data.get("createdBy", "unknown") 

    # 1. Unique Name Check
    await cur.execute(
        "SELECT * FROM Event WHERE group_name = %s AND event_name = %s", 
        (group_name, event["eventName"])
    )
    if await cur.fetchone():
        return JSONResponse({"error": "Event name must be unique in this group"}, status_code=400)

    try:
        # --- START TRANSACTION ---
        
        # 2. Insert Event
        await cur.execute(
            queries.CREATE_EVENT,
            (group_name, event["eventName"], current_user, event.get("description", ""), event.get("duration", ""))
        )
        
        # 3. Validate & Insert Transactions
        for txn in event.get("transactions", []):
            owed_by = txn["owedBy"]
            owed_to = txn["owedTo"]

            # FIX 1: Prevent self-payment
            if owed_by == owed_to:
                await cur._connection.rollback()
                return JSONResponse({"error": "Users cannot owe money to themselves."}, status_code=400)

            # FIX 2: Validate User Existence (Prevents Error 1452)
            await cur.execute("SELECT username FROM User WHERE username = %s", (owed_by,))
            if not await cur.fetchone():
                await cur._connection.rollback()
                return JSONResponse({"error": f"User '{owed_by}' does not exist."}, status_code=400)

            await cur.execute("SELECT username FROM User WHERE username = %s", (owed_to,))
            if not await cur.fetchone():
                await cur._connection.rollback()
                return JSONResponse({"error": f"User '{owed_to}' does not exist."}, status_code=400)

            # 4. Insert Transaction
            await cur.execute(
                queries.CREATE_TRANSACTION,
                (
                    group_name, event["eventName"], current_user, 
                    owed_by, owed_to, txn["amount"], 
                    txn.get("reason", ""), datetime.now()
                )
            )
        
        await cur._connection.commit()
        return JSONResponse({"success": True})

    except Exception as e:
        await cur._connection.rollback()
        print(f"Error adding event: {e}")
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)

@app.post("/api/groups/updateMembers")
async def update_members(req: Request, cur: Annotated[Cur, Depends(get_db)]):
    data = await req.json()
    group_name = data["groupName"]
    created_by = data["createdBy"]
    members = data.get("members", [])
    
    await cur.execute(queries.DELETE_GROUP_MEMBERS, (group_name, created_by))
    
    for member_id in members:
        if member_id.strip():
            await cur.execute(queries.ADD_GROUP_MEMBER, (group_name, created_by, member_id.strip()))
    
    await cur._connection.commit()
    return JSONResponse({"message": "Group members updated"})


# TRANSACTIONS
@app.post("/api/uploadReceiptOnly")
async def upload_receipt(
    groupName: str = Form(...),
    eventName: str = Form(...),
    timestamp: str = Form(...),
    owedBy: str = Form(...),
    owedTo: str = Form(...),
    receipt: UploadFile = File(...),
    cur: Annotated[Cur, Depends(get_db)] = None
):
    # File saving...
    filename = f"receipt_{datetime.now().timestamp()}_{receipt.filename}"
    filepath = os.path.join("uploads", filename)
    with open(filepath, "wb") as f:
        f.write(await receipt.read())

    await cur.execute(queries.GET_TRANSACTION_BY_DETAILS, (groupName, eventName, timestamp, owedBy, owedTo))
    transaction = await cur.fetchone()
    
    if not transaction:
        return JSONResponse({"error": "Transaction not found"}, status_code=404)
    
    await cur.execute(queries.UPDATE_TRANSACTION_RECEIPT, (f"/uploads/{filename}", transaction["transaction_id"]))
    await cur._connection.commit()
    return JSONResponse({"message": "Receipt uploaded"})

@app.post("/api/markTransactionPaid")
async def mark_paid(req: Request, cur: Annotated[Cur, Depends(get_db)]):
    data = await req.json()
    
    await cur.execute(
        queries.GET_TRANSACTION_BY_DETAILS, 
        (data["groupName"], data["eventName"], data["timestamp"], data["owedBy"], data["owedTo"])
    )
    transaction = await cur.fetchone()
    
    if not transaction:
        return JSONResponse({"error": "Transaction not found"}, status_code=404)
    
    await cur.execute(queries.MARK_TRANSACTION_PAID, (transaction["transaction_id"],))
    await cur._connection.commit()
    return JSONResponse({"message": "Marked as paid"})


@app.get("/receipt_upload", response_class=HTMLResponse)
async def receipt_upload_page(
    req: Request,
    groupName: str,  # <--- Updated to match URL parameter
    eventName: str,
    timestamp: str,
    owedBy: str,
    owedTo: str
):
    return templates.TemplateResponse(
        req, "receipt_upload.html",
        {
            "groupName": groupName, # Updated context key
            "eventName": eventName,
            "timestamp": timestamp,
            "owedBy": owedBy,
            "owedTo": owedTo
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)