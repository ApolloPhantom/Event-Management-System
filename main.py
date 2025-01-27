import os
from datetime import datetime,timedelta,date
import random
from typing import *
from functools import wraps
from fastapi import FastAPI, Request, Response, HTTPException, Depends,Form
from fastapi.responses import RedirectResponse,JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from supabase import create_client, Client
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from requests.exceptions import RequestException
import requests
from typing import Optional, Dict
import jwt
from dotenv import load_dotenv
from fpdf import FPDF
from pydantic import BaseModel, EmailStr
import uuid

load_dotenv()
base_path = os.path.dirname(os.path.abspath(__file__))
stat = "static"
stat_path = os.path.join(base_path, stat)
app = FastAPI()
app.mount("/static", StaticFiles(directory=stat_path), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    #secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key"),  # Change this in production
    secret_key = ("asdljjhbjb","77896s98s"),
    max_age=None  # Session will last until browser closes
)

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)



security = HTTPBearer()

async def verify_operator_token(request: Request):
    session = request.session
    if not session.get("o_id"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return session.get("o_id")


def o_login_required(func):
    @wraps(func)
    async def wrapper(*args, request: Request, **kwargs):
        session = request.session
        if not session.get("o_id"):
            return RedirectResponse(url="/O_login", status_code=303)
        return await func(*args, request=request, **kwargs)
    return wrapper

# Middleware to prevent caching
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response

MEME_API_URL = 'https://meme-api.com/gimme'
FALLBACK_MEMES = [
    '/static/fallback_meme1.jpg',
    '/static/fallback_meme2.jpg',
    '/static/fallback_meme3.jpg',
]

async def get_meme() -> Optional[Dict[str, str]]:
    try:
        response = requests.get(MEME_API_URL, timeout=5)
        response.raise_for_status()
        meme_data = response.json()
        return {
            'url': meme_data['url'],
            'title': meme_data.get('title', 'Funny Meme')
        }
    except RequestException as e:
        app.logger.error(f"Error fetching meme: {str(e)}")
        return None

@app.get("/error")
async def error_get(request: Request):
    error = request.session.get("error", "Unknown error") 
    request.session.pop("error",None)
    return templates.TemplateResponse("Error.html", {"request": request, "error": error})

@app.get("/get_meme")
async def fetch_meme():
    meme = await get_meme()
    if meme:
        return JSONResponse(content=meme)
    else:
        fallback_meme = {
            'url': f"/static/{FALLBACK_MEMES[0]}",
            'title': 'Fallback Meme'
        }
        return JSONResponse(
            status_code=503,  # Service Unavailable
            content=fallback_meme
        )

def calculate_event_timeline(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    now = datetime.now()
    total_duration = (end_date - start_date).days
    
    if now < start_date:
        status = "Upcoming"
        time_left = (start_date - now).days
        progress = 0
    elif now > end_date:
        status = "Completed"
        time_left = 0
        progress = 100
    else:
        status = "In Progress"
        time_left = (end_date - now).days
        elapsed = (now - start_date).days
        progress = min(100, int((elapsed / total_duration) * 100))
    
    return {
        "status": status,
        "time_left": time_left,
        "progress": progress,
        "total_duration": total_duration
    }

def serialize_event(event: Dict[str, Any], venues: List[Dict[str, Any]], schedules: List[Dict[str, Any]]) -> Dict[str, Any]:
    serialized = event.copy()
    start_date = datetime.strptime(serialized['S_Date'], '%Y-%m-%d') if serialized.get('S_Date') else None
    end_date = datetime.strptime(serialized['E_Date'], '%Y-%m-%d') if serialized.get('E_Date') else None
    
    if start_date and end_date:
        duration = (end_date - start_date).days
        timeline_info = calculate_event_timeline(start_date, end_date)
        serialized.update({
            "duration": duration,
            "timeline": timeline_info,
            "S_Date": start_date.strftime('%Y-%m-%d'),
            "E_Date": end_date.strftime('%Y-%m-%d')
        })
    
    # Add venue information
    venue = next((v for v in venues if v['V_Id'] == serialized.get('V_Id')), None)
    if venue:
        serialized['venue'] = venue
    
    # Add event schedules
    event_schedules = [s for s in schedules if s['E_Id'] == serialized['E_Id']]
    if event_schedules:
        serialized['schedules'] = event_schedules
    
    return serialized

# Modify the home route to fetch event schedules:
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        response1 = supabase.table("Event").select(
            "E_Id",
            "Name",
            "S_Date",
            "E_Date",
            "Hosting_Dept",
            "No_of_Schedules",
            "Starting_Capital",
            "V_Id"
        ).execute()
        
        response2 = supabase.table("Venue").select(
            "V_Id",
            "Name",
            "Address",
            "Capacity"
        ).execute()
        
        response3 = supabase.table("Event_Schedule").select(
            "ES_Id",
            "E_Id",
            "Programme_Name",
            "No_of_Participants",
            "Host_Name",
            "Amount_Required",
            "Status"
        ).execute()
        
        events = [serialize_event(event, response2.data, response3.data) for event in response1.data]
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "variable": "0",
                "events": events
            }
        )
    except Exception as e:
        request.session["error"] = str(e)
        return RedirectResponse(url="/error", status_code=303)


@app.get("/O_home")
@o_login_required
async def o_home(request: Request):
    try:
        # Fetch all necessary data
        events_response = supabase.table("Event").select(
            "E_Id", "Name", "S_Date", "E_Date", "Hosting_Dept",
            "No_of_Schedules", "Starting_Capital", "V_Id"
        ).execute()
        
        schedules_response = supabase.table("Event_Schedule").select(
            "ES_Id", "E_Id", "Programme_Name", "No_of_Participants",
            "Host_Name", "Amount_Required", "Status"
        ).execute()
        
        venues_response = supabase.table("Venue").select(
            "V_Id", "Name", "Address", "Rent", "Capacity"
        ).execute()
        
        events = events_response.data
        schedules = schedules_response.data
        venues = venues_response.data

        # Helper function to safely format dates
        def format_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                return date_str

        # Format currency values
        def format_currency(amount):
            if amount is None:
                return "Not set"
            return f"${amount:,.2f}"

        # Organize data with proper field mapping
        event_data = {}
        for event in events:
            event_data[event['E_Id']] = {
                'event': {
                    **event,
                    'S_Date': format_date(event.get('S_Date')),
                    'E_Date': format_date(event.get('E_Date')),
                    'Name': event.get('Name', 'Unnamed Event'),
                    'Hosting_Dept': event.get('Hosting_Dept', 'No Department'),
                    'No_of_Schedules': event.get('No_of_Schedules', 0),
                    'Starting_Capital': format_currency(event.get('Starting_Capital'))
                },
                'schedules': [],
                'venue': next(
                    (
                        {
                            **v,
                            'Name': v.get('Name', 'Unknown Venue'),
                            'Address': v.get('Address', 'No address specified'),
                            'Rent': format_currency(v.get('Rent')),
                            'Capacity': v.get('Capacity', 'Not specified')
                        }
                        for v in venues if v['V_Id'] == event.get('V_Id')
                    ),
                    None
                )
            }

        # Organize schedules with schema-specific fields
        for schedule in schedules:
            event_id = schedule.get('E_Id')
            if event_id and event_id in event_data:
                formatted_schedule = {
                    **schedule,
                    'Programme_Name': schedule.get('Programme_Name', 'Untitled Program'),
                    'No_of_Participants': schedule.get('No_of_Participants', 0) or 0,
                    'Host_Name': schedule.get('Host_Name', 'No host assigned'),
                    'Amount_Required': format_currency(schedule.get('Amount_Required')),
                    'Status': schedule.get('Status', False)
                }
                event_data[event_id]['schedules'].append(formatted_schedule)

        # Calculate dashboard statistics based on schema
        stats = {
            "total_events": len(events),
            "active_schedules": sum(1 for s in schedules if s.get('Status')),
            "total_participants": sum(s.get('No_of_Participants', 0) or 0 for s in schedules),
            "total_venues": len(venues)
        }

        return templates.TemplateResponse(
            "O_home.html",
            {
                "request": request,
                "event_data": event_data,
                "venues": venues,
                "stats": stats,
                "now": datetime.now
            }
        )
    except Exception as e:
        print(f"Error in o_home: {str(e)}")
        return RedirectResponse(url="/error", status_code=303)

@app.get("/B_dash", response_class=HTMLResponse)
async def budget_dashboard(request: Request):
    try:
        # Fetch raw data from tables independently
        budget_response = supabase.table("Budget").select("*").execute()
        event_response = supabase.table("Event").select("*").execute()
        sponsor_response = supabase.table("Sponsor").select("*").execute()

        # Convert response data to lists
        budgets = budget_response.data if budget_response else []
        events = event_response.data if event_response else []
        sponsors = sponsor_response.data if sponsor_response else []

        # Create lookup dictionaries for easier joining
        event_lookup = {event["E_Id"]: event for event in events}
        event_name_lookup = {event["Name"]: event for event in events}

        # Process budget data to include event names
        budget_data = []
        events_with_budget = set()
        for budget in budgets:
            event = event_lookup.get(budget["E_Id"])
            if event:
                budget_amount = budget["Amount"] or 0
                sponsor_funded = budget["Sponsor_Funded_Amount"] or 0
                budget_data.append({
                    "Amount": budget_amount,
                    "EventName": event["Name"],
                    "SponsorFundedAmount": sponsor_funded,
                    "TotalAmount": budget_amount + sponsor_funded  # Add total calculation
                })
                events_with_budget.add(event["Name"])

        # Process sponsor data to include event names
        sponsor_data = []
        for sponsor in sponsors:
            event = event_lookup.get(sponsor["E_Id"])
            if event:
                sponsor_data.append({
                    "Name": sponsor["Name"],
                    "Fund": sponsor["Fund"],
                    "Company_Name": sponsor["Company_Name"],
                    "EventName": event["Name"]
                })

        # Find events without budget using names
        events_without_budget = [
            {
                "Name": event["Name"],
                "S_Date": event["S_Date"],
                "E_Date": event["E_Date"],
                "Hosting_Dept": event["Hosting_Dept"],
                "No_of_Schedules": event["No_of_Schedules"],
                "Starting_Capital": event["Starting_Capital"]
            }
            for event in events 
            if event["Name"] not in events_with_budget
        ]

        # Calculate metrics
        total_budget = sum(b["Amount"] for b in budget_data if b.get("Amount"))
        total_sponsors = len(sponsor_data)
        pending_events = len(events_without_budget)

        # Prepare analytics data
        company_funds = {}
        event_sponsors = {}
        event_funds = {}

        # Process company funds and event-based metrics
        for sponsor in sponsor_data:
            # Company funds
            company = sponsor.get("Company_Name", "Unspecified")
            fund = sponsor.get("Fund", 0) or 0
            company_funds[company] = company_funds.get(company, 0) + fund

            # Event-based metrics
            event_name = sponsor.get("EventName", "Unassigned")
            if event_name not in event_sponsors:
                event_sponsors[event_name] = set()
            event_sponsors[event_name].add(sponsor["Name"])  # Use sponsor name instead of ID
            event_funds[event_name] = event_funds.get(event_name, 0) + fund

        # Convert event sponsors to counts
        sponsors_per_event = {
            event: len(sponsors) 
            for event, sponsors in event_sponsors.items()
        }

        # Sort analytics data
        analytics_data = {
            "company_funds": dict(sorted(
                company_funds.items(), 
                key=lambda x: x[1], 
                reverse=True
            )),
            "sponsors_per_event": dict(sorted(
                sponsors_per_event.items(), 
                key=lambda x: x[1], 
                reverse=True
            )),
            "sponsor_money_per_event": dict(sorted(
                event_funds.items(), 
                key=lambda x: x[1], 
                reverse=True
            ))
        }

        return templates.TemplateResponse(
            "B_Dash.html",
            {
                "request": request,
                "budget_data": budget_data,
                "sponsor_data": sponsor_data,
                "events_without_budget": events_without_budget,
                "total_budget": total_budget,
                "total_sponsors": total_sponsors,
                "pending_events": pending_events,
                "analytics_data": analytics_data
            }
        )
    except Exception as e:
        print(f"Error in budget_dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/O_register", response_class=HTMLResponse)
async def o_register_get(request: Request):
    if request.session.get("o_id"):
        return RedirectResponse(url="/O_home")
    return templates.TemplateResponse("O_register.html", {"request": request})

@app.post("/O_register")
async def o_register_post(
    request: Request,
    name: str = Form(...),
    password: Optional[str] = Form(None),
    s_key: int = Form(...)
):
    try:
        response = supabase.table("Organizer") \
            .select("*") \
            .eq("Name", name) \
            .eq("Password", password) \
            .eq("Security_Key", s_key) \
            .execute()
            
        if len(response.data) > 0:
            return ""

        existing_ids = supabase.table("Organizer") \
            .select("O_Id") \
            .execute()

        existing_id_list = [record["O_Id"] for record in existing_ids.data]

        gen_id = random.randint(1, 1000)
        while gen_id in existing_id_list:
            gen_id = random.randint(1, 1000)

        response = supabase.table("Organizer") \
            .insert({
                "O_Id": gen_id,
                "Name": name,
                "Password": password,
                "Security_Key": s_key
            }) \
            .execute()

        request.session["o_id"] = gen_id
        request.session["name"] = name
        
        return str(gen_id)

    except Exception as e:
        print("Error:", type(e).__name__, str(e))
        raise HTTPException(status_code=500, detail="Registration failed")
    
@app.get("/O_login", response_class=HTMLResponse)
async def o_login_get(request: Request):
    # Redirect if already logged in
    if request.session.get("o_id"):
        return RedirectResponse(url="/O_home")
    return templates.TemplateResponse("O_login.html", {"request": request})

@app.post("/O_login")
async def o_login_post(
    request: Request,
    id: int = Form(...),
    password: str = Form(...)
):
    try:
        response = supabase.table("Organizer") \
            .select("*") \
            .eq("O_Id", id) \
            .eq("Password", password) \
            .execute()

        if not response.data:
            return 0

        organizer = response.data[0]
        request.session["o_id"] = organizer["O_Id"]
        request.session["name"] = organizer["Name"]
        return 1

    except ValueError as ve:
        print("Validation Error:", str(ve))
        return 0
    except Exception as e:
        print("Error:", type(e).__name__, str(e))
        return 0

@app.get("/O_logout")
@o_login_required
async def o_logout(request:Request):
    request.session.clear()
    return RedirectResponse(url="/O_login")

@app.get("/O_change", response_class=HTMLResponse)
@o_login_required
async def change_password_page(request: Request):
    return templates.TemplateResponse(
        "O_change_password.html",
        {"request": request}
    )

@app.post("/O_change")
@o_login_required
async def change_password(
    request: Request,
    password: str = Form(...),
    password1: str = Form(...),
    s_key: str = Form(...),
):
    try:
        # Check security key
        result = supabase.table("Organizer") \
            .select("O_Id") \
            .eq("O_Id", request.session.get("o_id")) \
            .eq("Security_Key", s_key) \
            .execute()
        
        if not result.data:
            return ""

        # Update password
        update_result = supabase.table("Organizer") \
            .update({"Password": password}) \
            .eq("O_Id", request.session.get("o_id")) \
            .execute()

        if update_result.data:
            return "Success"
        return ""

    except Exception as e:
        print(f"Error:- {type(e).__name__}")
        return ""

@app.get("/E_register", response_class=HTMLResponse)
async def get_event_register(request: Request):
    try:
        # Query all venues from Supabase
        response = supabase.table('Venue').select("*").execute()
        venues = response.data
        
        return templates.TemplateResponse(
            "E_register.html",
            {"request": request, "options": venues}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/E_register")
async def create_event(
    e_name: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    host_dept: str = Form(...),
    schedule: int = Form(...),
    s_cap: float = Form(...),
    venue: int = Form(...)
):
    try:
        # Check if event already exists
        existing_event = supabase.table('Event').select("*").eq('Name', e_name)\
            .eq('S_Date', start_date)\
            .eq('E_Date', end_date)\
            .eq('Hosting_Dept', host_dept)\
            .eq('No_of_Schedules', schedule)\
            .eq('Starting_Capital', s_cap)\
            .execute()

        if existing_event.data:
            return ""

        # Insert new event
        new_event = {
            "Name": e_name,
            "S_Date": str(start_date),
            "E_Date": str(end_date),
            "Hosting_Dept": host_dept,
            "No_of_Schedules": schedule,
            "Starting_Capital": s_cap,
            "V_Id": venue
        }
        
        response = supabase.table('Event').insert(new_event).execute()
        
        if response.data:
            # Return the generated E_Id
            return str(response.data[0]['E_Id'])
        else:
            return ""

    except Exception as e:
        print(f"Error:- {type(e).__name__}")
        return ""

@app.get("/V_register", response_class=HTMLResponse)
async def get_venue_register(request: Request):
    return templates.TemplateResponse("V_register.html", {"request": request})

@app.post("/V_register")
async def create_venue(
    v_name: str = Form(...),
    address: str = Form(...),
    rent: int = Form(...),
    cap: int = Form(...)
):
    try:
        # Check if venue already exists
        existing_venue = supabase.table("Venue") \
            .select("*") \
            .eq("Name", v_name) \
            .eq("Address", address) \
            .eq("Rent", rent) \
            .eq("Capacity", cap) \
            .execute()

        if len(existing_venue.data) > 0:
            return ""  # Return empty string if venue already exists

        # Insert new venue
        result = supabase.table("Venue") \
            .insert({
                "Name": v_name,
                "Address": address,
                "Rent": rent,
                "Capacity": cap
            }) \
            .execute()

        # If insertion successful, return the generated V_Id
        if result.data and len(result.data) > 0:
            return str(result.data[0]["V_Id"])
        else:
            return ""

    except Exception as e:
        print(f"Error:- {type(e).__name__}")
        print(f"Error details: {str(e)}")
        return ""
    
@app.get("/E_schedule")
async def get_event_schedule(request: Request):
    try:
        # Fetch all events from the Event table
        response = supabase.table("Event").select("*").execute()
        events = response.data
        
        return templates.TemplateResponse(
            "E_schedule.html",
            {"request": request, "options": events}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/E_schedule")
async def create_event_schedule(
    event: int = Form(...),
    p_name: str = Form(...),
    part: int = Form(...),
    h_name: str = Form(...),
    a_req: int = Form(...),
    stat: str = Form(...)
):
    try:
        # Convert Y/N to boolean
        status_bool = True if stat.upper() == 'Y' else False
        
        # Check for existing schedule with same details
        existing = supabase.table("Event_Schedule") \
            .select("*") \
            .eq("E_Id", event) \
            .eq("Programme_Name", p_name) \
            .eq("Host_Name", h_name) \
            .eq("Amount_Required", a_req) \
            .execute()
        
        if existing.data:
            return JSONResponse(content="", status_code=400)
        
        # Check number of schedules
        current_schedules = supabase.table("Event_Schedule") \
            .select("*") \
            .eq("E_Id", event) \
            .execute()
            
        event_details = supabase.table("Event") \
            .select("No_of_Schedules") \
            .eq("E_Id", event) \
            .execute()
            
        if len(current_schedules.data) >= event_details.data[0]["No_of_Schedules"]:
            return JSONResponse(content="", status_code=400)
        
        # Insert new schedule
        # Note: ES_Id is auto-generated by Supabase
        new_schedule = supabase.table("Event_Schedule") \
            .insert({
                "E_Id": event,
                "Programme_Name": p_name,
                "No_of_Participants": part,
                "Host_Name": h_name,
                "Amount_Required": a_req,
                "Status": status_bool
            }) \
            .execute()
            
        if new_schedule.data:
            # Return the generated ES_Id
            return JSONResponse(
                content=str(new_schedule.data[0]["ES_Id"]), 
                status_code=200
            )
        else:
            return JSONResponse(content="", status_code=400)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse(content="", status_code=500)


@app.get("/B_create", response_class=HTMLResponse)
async def get_budget_form(request: Request):
    try:
        # Fetch all events from Supabase
        response = supabase.table("Event").select("*").execute()
        events = response.data
        
        return templates.TemplateResponse(
            "B_Create.html",
            {"request": request, "options": events}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/B_create")
async def create_budget(
    event: int = Form(...),
    a_req: float = Form(...)
):
    try:
        # Insert new budget record
        response = supabase.table("Budget").insert({
            "E_Id": event,
            "Amount": a_req,
            "Sponsor_Funded_Amount": 0
        }).execute()
        
        if response.data:
            return response.data[0]["E_Id"]
        return ""
        
    except Exception as e:
        print(f"Error: {type(e).__name__} - {str(e)}")
        return ""

@app.get("/S_register",response_class=HTMLResponse)
async def get_sponsor_register(request: Request):
    try:
        response = supabase.table('Event').select("*").execute()
        events = response.data
        return templates.TemplateResponse("S_register.html", {"request": request,"options": events})
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
     

@app.post("/S_register")
async def create_sponsor(
    request: Request,
    name: str = Form(...),
    fund: float = Form(...),
    c_name: str = Form(...),
    event: int = Form(...),
):
    try:
        # Store registration data in session
        request.session["sponsor_data"] = {
            "Name": name,
            "Fund": fund,
            "Company_Name": c_name,
            "E_Id": event
        }
        
        # Redirect to payment portal
        return RedirectResponse(url="/Portal", status_code=303)
        
    except Exception as e:
        print(f"Error: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/S_Payment")
async def process_payment(
    request: Request,
    b_id: int = Form(...),
    pin: int = Form(...)
):
    try:
        sponsor_data = request.session.get("sponsor_data")
        if not sponsor_data:
            raise HTTPException(status_code=400, detail="No pending registration found")

        bank_data = supabase.table("Bank").select("*").eq("Bank_Id", b_id).execute()
        
        if not bank_data.data:
            raise HTTPException(status_code=400, detail="Invalid bank details")
            
        bank = bank_data.data[0]
        if bank["PIN"] != pin:
            raise HTTPException(status_code=400, detail="Invalid PIN")
        
        if bank["Total_Amount"] < sponsor_data["Fund"]:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        # Begin transaction
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
        new_balance = bank["Total_Amount"] - sponsor_data["Fund"]
        supabase.table("Bank").update({"Total_Amount": new_balance}).eq("Bank_Id", b_id).execute()
        
        # Get bank name for receipt
        bank_name = supabase.table("Bank").select("Name").eq("Bank_Id", b_id).execute()
        
        # Update Budget table
        budget_data = supabase.table("Budget").select("*").eq("E_Id", sponsor_data["E_Id"]).execute()
        
        if budget_data.data:
            current_sponsored_amount = budget_data.data[0].get("Sponsor_Funded_Amount") or 0
            new_sponsored_amount = current_sponsored_amount + sponsor_data["Fund"]
            
            supabase.table("Budget").update({
                "Sponsor_Funded_Amount": new_sponsored_amount
            }).eq("E_Id", sponsor_data["E_Id"]).execute()
        else:
            # Create new budget record if it doesn't exist
            supabase.table("Budget").insert({
                "E_Id": sponsor_data["E_Id"],
                "Amount": 0,  # Initial budget amount
                "Sponsor_Funded_Amount": sponsor_data["Fund"]
            }).execute()
        
        # Generate receipt
        receipt = generate_receipt(
            transaction_id=transaction_id,
            sponsor_name=sponsor_data["Name"],
            company_name=sponsor_data["Company_Name"],
            amount=sponsor_data["Fund"],
            bank_id=bank_name.data[0]['Name'],
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        supabase.table("Receipt").insert({
            "Transaction_Id": transaction_id,
            "Sponsor_Name": sponsor_data["Name"],
            "Company_Name": sponsor_data["Company_Name"],
            "Amount": sponsor_data["Fund"],
            "Bank_Name": bank_name.data[0]['Name'],
            "Transaction_Date": datetime.now().isoformat() 
        }).execute()
        
        # Insert sponsor data
        supabase.table("Sponsor").insert(sponsor_data).execute()
        
        # Clear session
        request.session.pop("sponsor_data", None)
        
        return HTMLResponse(content=receipt, status_code=200)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail="Payment processing failed")

@app.get("/Portal")
async def payment_portal(request: Request):
    sponsor_data = request.session.get("sponsor_data")
    
    if not sponsor_data:
        return RedirectResponse(url="/S_register")
    return templates.TemplateResponse(
        "Portal.html",
        {
            "request": request,
            "amount": sponsor_data["Fund"],
            "company": sponsor_data["Company_Name"],
            "sponsor_name": sponsor_data["Name"]
        }
    )

def generate_receipt(transaction_id: str, sponsor_name: str, company_name: str, 
                    amount: float, bank_id: int, date: str) -> str:
    receipt_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .receipt-container {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #ccc;
                border-radius: 8px;
                font-family: Arial, sans-serif;
            }}
            .receipt-header {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .receipt-details {{
                margin-bottom: 15px;
            }}
            .receipt-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
            }}
            .success-message {{
                color: green;
                text-align: center;
                font-weight: bold;
                margin: 20px 0;
            }}
            @media print {{
                .no-print {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="receipt-container">
            <div class="receipt-header">
                <h2>Payment Receipt</h2>
                <div class="success-message">Payment Successful!</div>
            </div>
            
            <div class="receipt-details">
                <div class="receipt-row">
                    <span>Transaction ID:</span>
                    <span>{transaction_id}</span>
                </div>
                <div class="receipt-row">
                    <span>Date:</span>
                    <span>{date}</span>
                </div>
                <div class="receipt-row">
                    <span>Sponsor Name:</span>
                    <span>{sponsor_name}</span>
                </div>
                <div class="receipt-row">
                    <span>Company Name:</span>
                    <span>{company_name}</span>
                </div>
                <div class="receipt-row">
                    <span>Amount Paid:</span>
                    <span>${amount:.2f}</span>
                </div>
                <div class="receipt-row">
                    <span>Bank Name:</span>
                    <span>{bank_id}</span>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;" class="no-print">
                <button onclick="window.print()">Print Receipt</button>
                <button onclick="window.location.href='/'">Return to Home</button>
            </div>
        </div>
    </body>
    </html>
    """
    return receipt_html


@app.get("/S_Refund", response_class=HTMLResponse)
async def get_refund_form(request: Request):
    try:
        return templates.TemplateResponse(
            "S_Refund.html",
            {"request": request}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/S_Refund")
async def process_refund(
    request: Request,
    transaction_id: str = Form(...),
    sponsor_name: str = Form(...),
    company_name: str = Form(...),
    amount: float = Form(...),
    bank_name: str = Form(...),
    transaction_date: str = Form(...)
):
    try:
        # Convert string date to datetime
        trans_date = datetime.strptime(transaction_date, '%Y-%m-%d')
        
        # Verify receipt exists with all provided details
        receipt = supabase.table("Receipt").select("*")\
            .eq("Transaction_Id", transaction_id)\
            .eq("Sponsor_Name", sponsor_name)\
            .eq("Company_Name", company_name)\
            .eq("Amount", amount)\
            .eq("Bank_Name", bank_name)\
            .single().execute()
        
        if not receipt.data:
            return templates.TemplateResponse(
                "S_Refund.html",
                {
                    "request": request, 
                    "error": "No transaction found with these details",
                    "values": {
                        "transaction_id": transaction_id,
                        "sponsor_name": sponsor_name,
                        "company_name": company_name,
                        "amount": amount,
                        "bank_name": bank_name,
                        "transaction_date": transaction_date
                    }
                }
            )

        # Show bank details form if verification successful
        return templates.TemplateResponse(
            "bank_details.html",
            {
                "request": request,
                "transaction_id": transaction_id,
                "amount": amount,
                "bank_name": bank_name
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process_bank_details")
async def process_bank_details(
    request: Request,
    bank_id: int = Form(...),
    pin: int = Form(...),
    transaction_id: str = Form(...)
):
    try:
        # Verify bank details
        bank = supabase.table("Bank").select("*")\
            .eq("Bank_Id", bank_id)\
            .eq("PIN", pin)\
            .single().execute()
        
        if not bank.data:
            return templates.TemplateResponse(
                "bank_details.html",
                {
                    "request": request, 
                    "error": "Invalid bank details",
                    "transaction_id": transaction_id
                }
            )

        # Get receipt details
        receipt = supabase.table("Receipt").select("*")\
            .eq("Transaction_Id", transaction_id)\
            .single().execute()
        
        refund_amount = receipt.data["Amount"]

        # Update bank balance
        supabase.table("Bank").update({"Total_Amount": bank.data["Total_Amount"] + refund_amount})\
            .eq("Bank_Id", bank_id).execute()

        # Delete sponsor record
        supabase.table("Sponsor").delete()\
            .eq("Name", receipt.data["Sponsor_Name"])\
            .eq("Company_Name", receipt.data["Company_Name"])\
            .execute()

        # Update receipt with refund status
        supabase.table("Receipt").delete().eq("Transaction_Id", transaction_id).execute()

        return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/A_register",response_class=HTMLResponse)
async def get_register_form(request: Request):
    try:
        return templates.TemplateResponse(
            "A_register.html",
            {"request": request}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

