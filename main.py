import os
from datetime import datetime,timedelta
from typing import *
from functools import wraps
from fastapi import FastAPI, Request, Response, HTTPException, Depends
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

# supabase: Client = create_client(
#     os.getenv("SUPABASE_URL"),
#     os.getenv("SUPABASE_KEY")
# )

supabase: Client = create_client(
    "https://mfpblhjctozquhebtuiy.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1mcGJsaGpjdG96cXVoZWJ0dWl5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyOTU1OTY0NCwiZXhwIjoyMDQ1MTM1NjQ0fQ.3Hkko-Pq7ksBbv7Qa7q-0UrOAeJAuNMNChKqBO2l7sk"
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

        # Process budget data to include event names
        budget_data = []
        events_with_budget = set()
        for budget in budgets:
            event = event_lookup.get(budget["E_Id"])
            budget_data.append({
                "B_Id": budget["B_Id"],
                "Amount": budget["Amount"],
                "E_Id": budget["E_Id"],
                "EventName": event["Name"] if event else "Unassigned"
            })
            if event:
                events_with_budget.add(budget["E_Id"])

        # Process sponsor data to include event names
        sponsor_data = []
        for sponsor in sponsors:
            event = event_lookup.get(sponsor["E_Id"])
            sponsor_data.append({
                "S_Id": sponsor["S_Id"],
                "Name": sponsor["Name"],
                "Fund": sponsor["Fund"],
                "Company_Name": sponsor["Company_Name"],
                "E_Id": sponsor["E_Id"],
                "EventName": event["Name"] if event else "Unassigned"
            })

        # Find events without budget
        events_without_budget = [
            event for event in events 
            if event["E_Id"] not in events_with_budget
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
            event_sponsors[event_name].add(sponsor["S_Id"])
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