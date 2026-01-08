from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Annotated, Optional
from datetime import datetime, timedelta  # FIXED: Added timedelta import
import os
from pathlib import Path
from .trip_planner import TripPlanner
import json
from .db import connect_to_db, get_db, Cur
from .config import get_config
from . import queries
from .chatbot.router import router as chatbot_router 


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
os.makedirs(str(BASE_DIR / "static"), exist_ok=True)  

# Mount static files and uploads
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), "static")  
app.mount("/uploads", StaticFiles(directory="uploads"), "uploads")

# Include chatbot router
app.include_router(chatbot_router) 
 
config = get_config()
trip_planner = TripPlanner(aviation_api_key=config.aviation_api_key)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(req: Request, exc: StarletteHTTPException):
    return templates.TemplateResponse(
        req,
        "error.html",
        {"status": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code
    )

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/images/logo.png")

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
    username: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    mobile: str = Form(...),
    currency: str = Form(...),
    password: str = Form(...)
):
    await cur.execute(queries.GET_USER, (username,))
    if await cur.fetchone():
        return templates.TemplateResponse(req, "signup.html", {"error": "Username already taken"})

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
    username: str = Form(...),
    password: str = Form(...)
):
    await cur.execute(queries.GET_USER, (username,))
    user = await cur.fetchone()
    
    if not user or user["password"] != password:
        return templates.TemplateResponse(req, "login.html", {"error": "Invalid credentials"})
    
    return RedirectResponse(url=f"/dashboard?userId={user['username']}", status_code=303)


# DASHBOARD
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(req: Request, userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_USER, (userId,))
    user = await cur.fetchone()
    
    if not user:
        raise StarletteHTTPException(status_code=404, detail="User not found")
    
    return templates.TemplateResponse(req, "dashboard.html", {"user": user, "userId": userId})


# PROFILE
@app.get("/profile", response_class=HTMLResponse)
async def profile(req: Request, userId: str, cur: Annotated[Cur, Depends(get_db)]):
    await cur.execute(queries.GET_USER, (userId,))
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
            # Convert datetime objects to strings for JSON serialization
            if event_dict.get("created_at"):
                event_dict["created_at"] = event_dict["created_at"].isoformat()
            event_dict["transactions"] = [
                {
                    **dict(t),
                    'amount': float(t['amount']) if t.get('amount') is not None else 0.0,
                    'timestamp': t['timestamp'].isoformat() if t.get('timestamp') else None
                }
                for t in transactions
            ]
            events_with_transactions.append(event_dict)
        
        group_dict = dict(group)
        # Convert datetime for group as well
        if group_dict.get("created_at"):
            group_dict["created_at"] = group_dict["created_at"].isoformat()
        
        # Convert members and handle Decimal types
        group_dict["members"] = [
            {
                **dict(m),
                "debt": float(m["debt"]) if m.get("debt") is not None else 0.0
            }
            for m in members
        ]
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
    
    await cur.execute("SELECT * FROM `Group` WHERE group_name = %s", (group_name,))
    if await cur.fetchone():
        return JSONResponse(
            {"error": f"The group name '{group_name}' is already taken. Please choose another name."}, 
            status_code=400
        )

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
        await cur.execute(
            queries.CREATE_GROUP, 
            (group_name, creator_id, data.get("duration", ""))
        )
        
        if creator_id not in clean_members:
            clean_members.append(creator_id)

        for member_id in clean_members:
            await cur.execute(queries.ADD_GROUP_MEMBER, (group_name, member_id))
        
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

    await cur.execute(
        "SELECT * FROM Event WHERE group_name = %s AND event_name = %s", 
        (group_name, event["eventName"])
    )
    if await cur.fetchone():
        return JSONResponse({"error": "Event name must be unique in this group"}, status_code=400)

    try:
        await cur.execute(
            queries.CREATE_EVENT,
            (group_name, event["eventName"], current_user, event.get("description", ""), event.get("duration", ""))
        )
        
        for txn in event.get("transactions", []):
            owed_by = txn["owedBy"]
            owed_to = txn["owedTo"]

            if owed_by == owed_to:
                await cur._connection.rollback()
                return JSONResponse({"error": "Users cannot owe money to themselves."}, status_code=400)

            await cur.execute("SELECT username FROM User WHERE username = %s", (owed_by,))
            if not await cur.fetchone():
                await cur._connection.rollback()
                return JSONResponse({"error": f"User '{owed_by}' does not exist."}, status_code=400)

            await cur.execute("SELECT username FROM User WHERE username = %s", (owed_to,))
            if not await cur.fetchone():
                await cur._connection.rollback()
                return JSONResponse({"error": f"User '{owed_to}' does not exist."}, status_code=400)

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
    groupName: str,
    eventName: str,
    timestamp: str,
    owedBy: str,
    owedTo: str
):
    return templates.TemplateResponse(
        req, "receipt_upload.html",
        {
            "groupName": groupName,
            "eventName": eventName,
            "timestamp": timestamp,
            "owedBy": owedBy,
            "owedTo": owedTo
        }
    )

# TRIP PLANNING ROUTES
@app.get("/plan-solo-trip", response_class=HTMLResponse)
async def plan_solo_trip_page(req: Request, userId: str):
    return templates.TemplateResponse(
        req, "plan_trip.html", 
        {"userId": userId, "isSolo": True, "groupName": None}
    )


@app.get("/plan-group-trip", response_class=HTMLResponse)
async def plan_group_trip_page(req: Request, userId: str, groupName: str):
    return templates.TemplateResponse(
        req, "plan_trip.html",
        {"userId": userId, "isSolo": False, "groupName": groupName}
    )


@app.post("/api/trips/calculate")
async def calculate_trip(req: Request):
    """Calculate all possible routes using Hamiltonian path algorithm"""
    data = await req.json()
    
    trip_name = data.get("tripName")
    start_date_str = data.get("startDate")
    destinations = data.get("destinations", [])
    
    if not trip_name or not start_date_str or len(destinations) < 2:
        return JSONResponse(
            {"error": "Trip name, start date, and at least 2 destinations required"}, 
            status_code=400
        )
    
    try:
        start_date = datetime.fromisoformat(start_date_str)
        result = trip_planner.calculate_trip_plan(destinations, start_date)
        
        if result.get("error"):
            return JSONResponse(result, status_code=400)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"Error calculating trip: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

    
@app.post("/api/trips/save")
async def save_trip(req: Request, cur: Annotated[Cur, Depends(get_db)]):
    """Save a calculated trip to the database"""
    data = await req.json()
    
    trip_name = data.get("tripName")
    group_name = data.get("groupName")
    created_by = data.get("createdBy")
    start_date_str = data.get("startDate")
    destinations = data.get("destinations", [])
    route_data = data.get("routeData", {})
    
    if not trip_name or not created_by or len(destinations) < 2:
        return JSONResponse(
            {"error": "Trip name, creator, and at least 2 destinations required"}, 
            status_code=400
        )
    
    try:
        start_date = datetime.fromisoformat(start_date_str)
        
        # Create trip
        await cur.execute(
            queries.CREATE_TRIP,
            (trip_name, group_name, created_by, "economy")
        )
        trip_id = cur.lastrowid
        
        # Get the optimal path from route_data
        optimal_path_indices = route_data.get("paths", [{}])[0].get("path_indices", list(range(len(destinations))))
        
        # Add destinations in optimal order
        destination_ids = []
        for visit_order, city_idx in enumerate(optimal_path_indices):
            dest = destinations[city_idx]
            
            # Calculate dates
            cumulative_days = sum(destinations[optimal_path_indices[i]]["days"] for i in range(visit_order))
            arrival_date = start_date + timedelta(days=cumulative_days)
            departure_date = arrival_date + timedelta(days=dest["days"])
            
            await cur.execute(
                queries.ADD_DESTINATION,
                (
                    trip_id,
                    dest["city"],
                    dest["country"],
                    dest.get("airport"),
                    dest.get("latitude"),
                    dest.get("longitude"),
                    visit_order + 1,
                    arrival_date,
                    departure_date
                )
            )
            destination_ids.append(cur.lastrowid)
        
        # Save pathway calculation
        await cur.execute(
            queries.SAVE_PATHWAY,
            (
                trip_id,
                json.dumps(optimal_path_indices),
                None,
                route_data.get("num_paths", 1),
                True
            )
        )
        
        await cur._connection.commit()
        
        return JSONResponse({
            "success": True,
            "trip_id": trip_id,
            "message": f"Trip '{trip_name}' saved successfully!"
        })
        
    except Exception as e:
        await cur._connection.rollback()
        print(f"Error saving trip: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/trips")
async def get_trips(userId: str, groupName: Optional[str] = None, 
                   cur: Annotated[Cur, Depends(get_db)] = None):
    """Get trips for a user or group"""
    try:
        if groupName:
            await cur.execute(queries.GET_TRIPS_FOR_GROUP, (groupName,))
        else:
            await cur.execute(queries.GET_TRIPS_FOR_USER, (userId, userId))
        
        trips = await cur.fetchall()
        
        result = []
        for trip in trips:
            trip_dict = dict(trip)
            trip_dict["created_at"] = trip_dict["created_at"].isoformat()
            
            # Get destinations
            await cur.execute(queries.GET_DESTINATIONS_FOR_TRIP, (trip["trip_id"],))
            destinations = await cur.fetchall()
            trip_dict["destinations"] = [
                {
                    **dict(d),
                    "latitude": float(d["latitude"]) if d.get("latitude") else None,
                    "longitude": float(d["longitude"]) if d.get("longitude") else None,
                    "arrival_date": d["arrival_date"].isoformat() if d.get("arrival_date") else None,
                    "departure_date": d["departure_date"].isoformat() if d.get("departure_date") else None
                }
                for d in destinations
            ]
            
            # Get routes
            await cur.execute(queries.GET_ROUTES_FOR_TRIP, (trip["trip_id"],))
            routes = await cur.fetchall()
            trip_dict["routes"] = [
                {
                    **dict(r),
                    "flight_cost": float(r["flight_cost"]) if r.get("flight_cost") else None,
                    "departure_time": r["departure_time"].isoformat() if r.get("departure_time") else None,
                    "arrival_time": r["arrival_time"].isoformat() if r.get("arrival_time") else None
                }
                for r in routes
            ]
            
            # Get optimal pathway
            await cur.execute(queries.GET_OPTIMAL_PATHWAY, (trip["trip_id"],))
            pathway = await cur.fetchone()
            if pathway:
                trip_dict["optimal_pathway"] = {
                    **dict(pathway),
                    "total_cost": float(pathway["total_cost"]) if pathway.get("total_cost") else None
                }
            
            result.append(trip_dict)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"Error fetching trips: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/trip/{trip_id}", response_class=HTMLResponse)
async def view_trip(req: Request, trip_id: int, userId: str, cur: Annotated[Cur, Depends(get_db)]):
    """View trip details and destinations"""
    await cur.execute(queries.GET_TRIP_BY_ID, (trip_id,))
    trip = await cur.fetchone()
    
    if not trip:
        raise StarletteHTTPException(status_code=404, detail="Trip not found")
    
    await cur.execute(queries.GET_DESTINATIONS_FOR_TRIP, (trip_id,))
    destinations = await cur.fetchall()
    
    await cur.execute(queries.GET_ROUTES_FOR_TRIP, (trip_id,))
    routes = await cur.fetchall()
    
    await cur.execute(queries.GET_OPTIMAL_PATHWAY, (trip_id,))
    pathway = await cur.fetchone()
    
    return templates.TemplateResponse(
        req, "view_trip.html",
        {
            "userId": userId,
            "trip": trip,
            "destinations": destinations,
            "routes": routes,
            "pathway": pathway
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)