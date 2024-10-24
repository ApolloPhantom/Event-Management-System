import os
import requests
from requests.exceptions import RequestException
import random
from functools import wraps
from flask import *
from flask_session import *
import sqlite3
import io

base = os.path.dirname(os.path.abspath(__file__))
db = "project.db"
db_path = os.path.join(base,db)

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

m = ["POST","GET"]

def o_login_required(f):
    @wraps(f)
    def decorator(*args,**kwargs):
        if session.get("o_id") is None:
            return redirect("/O_login")
        return f(*args,**kwargs)
    return decorator

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/error',methods=["GET"])
def error_post():
    if request.method == "GET":
        return render_template("Error.html",error=session["error"])

MEME_API_URL = 'https://meme-api.com/gimme'
FALLBACK_MEMES = [
    '/static/fallback_meme1.jpg',
    '/static/fallback_meme2.jpg',
    '/static/fallback_meme3.jpg',
]
def get_meme():
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

@app.route('/get_meme')
def fetch_meme():
    meme = get_meme()
    if meme:
        return jsonify(meme)
    else:
        fallback_meme = {
            'url': app.static_url_path + '/' + FALLBACK_MEMES[0],
            'title': 'Fallback Meme'
        }
        return jsonify(fallback_meme), 503  # Service Unavailable
@app.route("/O_register",methods=m)
def o_register():
    if request.method == "GET":
        return render_template("O_register.html")
    else:
        name = request.form.get('name')
        password = request.form.get('password')
        s_key = int(request.form.get('s_key'))
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Name = ? and Password = ? and Security_Key = ?",(name,password,s_key,))
        r = cur.fetchall()
        if len(r) > 0:
            return ""
        cur.execute("select O_ID from Organizer")
        r = cur.fetchall()
        gen_id = random.randint(1,1000)
        while(1):
            if len(r) == 0:
                break
            flag = 0
            for i in r:
                if i[0] == gen_id:
                    flag = 1
                    break
                else:
                    pass
            if flag == 1:
                gen_id = random.randint(1,1000)
            else:
                break
        try:
            cur.execute('insert into Organizer values(?,?,?,?)',(gen_id,name,password,s_key))
            con.commit()
            con.close()
            session["o_id"] = gen_id
            return str(gen_id)
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return ""

@app.route("/O_login",methods=m)
def o_login():
    try:
        if request.method == "GET":
            return render_template("O_login.html")
        else:
            id = int(request.form.get('id'))
            password = request.form.get('password')
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            try:
                cur.execute("select * from Organizer where O_ID = ? and Password = ?",(id,password,))
                r = cur.fetchall()
                con.close()
                if len(r) == 0:
                    return ""
                else:
                    session["o_id"] = id
                    return "Success"
            except Exception as e:
                print("Error:-",type(e).__name__)
                con.close()
                return ""
    except Exception as e:
        print("Error:-",type(e).__name__)
        return ""
        
@app.route("/O_logout")
@o_login_required
def o_logout():
    session.clear()
    return redirect("/O_login")

@app.route("/O_change",methods=m)
@o_login_required
def o_change():
    if request.method == "GET":
        return render_template("O_change_password.html")
    else:
        password = request.form.get('password')
        password1 = request.form.get('password1')
        s_key = request.form.get('s_key')
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        try:
            cur.execute("select O_ID from Organizer where O_ID = ? and Security_Key = ?",(session["o_id"],s_key,))
            r = cur.fetchall()
            if len(r) == 0:
                return ""
            cur.execute("update organizer set Password = ? where O_ID = ?",(password,session["o_id"],))
            con.commit()
            con.close()
            return "Success"
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return ""
    
@app.route("/O_home")
@o_login_required
def o_home():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Venue")
    venues = cursor.fetchall()
    cursor.execute("SELECT * FROM Event")
    events = cursor.fetchall()
    cursor.execute("SELECT * FROM Event_Schedule")
    event_schedules = cursor.fetchall()
    conn.close()
    event_data = {}
    for event in events:
        event_data[event[0]] = {'event': event, 'schedules': []}
    
    for schedule in event_schedules:
        event_id = schedule[1]
        if event_id in event_data:
            event_data[event_id]['schedules'].append(schedule)
    return render_template("O_home.html", venues=venues, event_data=event_data)

@app.route("/")
def home():
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("select * from Event")
    r = cur.fetchall()
    for i in range(0,len(r)):
        r[i] = list(r[i])
        
    return render_template("index.html",variable="0",events=r)

@app.route("/E_register",methods=m)
def e_register():
    if request.method == "GET":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Venue")
        r = cur.fetchall()
        con.close()
        return render_template("E_register.html",options=r)
    else:
        e_name = request.form.get("e_name")
        s_date = request.form.get("start_date")
        e_date = request.form.get("end_date")
        host_dept = request.form.get("host_dept")
        schedule = int(request.form.get("schedule"))
        s_cap = int(request.form.get("s_cap"))
        venue = int(request.form.get("venue")) 
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event where Name = ? and S_Date = ? and E_Date = ? and Hosting_Dept = ? and No_of_Schedules = ? and Starting_Capital = ?",(e_name,s_date,e_date,host_dept,schedule,s_cap,))
        r = cur.fetchall()
        if len(r) > 0:
            return ""
        cur.execute("select E_Id from Event")
        r = cur.fetchall()
        gen_id = random.randint(1,1000)
        while(1):
            if len(r) == 0:
                break
            flag = 0
            for i in r:
                if i[0] == gen_id:
                    flag = 1
                    break
                else:
                    pass
            if flag == 1:
                gen_id = random.randint(1,1000)
            else:
                break
        try:
            cur.execute('insert into Event values(?,?,?,?,?,?,?,?)',(gen_id,e_name,s_date,e_date,host_dept,schedule,s_cap,venue,))
            con.commit()
            con.close()
            return str(gen_id)
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return ""
        
        
@app.route("/V_register",methods=m)
def v_register():
    if request.method == "GET":
        return render_template("V_register.html")
    else:
        v_name = request.form.get("v_name")
        address = request.form.get("address")
        rent = int(request.form.get("rent"))
        cap = int(request.form.get("cap"))
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Venue where Name = ? and Address = ? and Rent = ? and Capacity = ?",(v_name,address,rent,cap,))
        r = cur.fetchall()
        if len(r) > 0:
            return ""
        cur.execute("select V_Id from Event")
        r = cur.fetchall()
        gen_id = random.randint(1,1000)
        while(1):
            if len(r) == 0:
                break
            flag = 0
            for i in r:
                if i[0] == gen_id:
                    flag = 1
                    break
                else:
                    pass
            if flag == 1:
                gen_id = random.randint(1,1000)
            else:
                break
        try:
            cur.execute('insert into Venue values(?,?,?,?,?)',(gen_id,v_name,address,rent,cap,))
            con.commit()
            con.close()
            return str(gen_id)
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return ""


@app.route("/E_schedule",methods=m)
def e_schedule():
    if request.method == "GET":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event")
        r = cur.fetchall()
        return render_template("E_schedule.html",options=r)
    else:
        event = int(request.form.get("event"))
        p_name = request.form.get("p_name")
        part = int(request.form.get("part"))
        h_name = request.form.get("h_name")
        a_req = int(request.form.get("a_req"))
        stat = request.form.get("stat")
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event_Schedule where E_Id = ? and Programme_Name = ? and Host_Name = ? and Amount_required = ?",(event,p_name,h_name,a_req,))
        r = cur.fetchall()
        if len(r) > 0:
            return ""
        cur.execute("select count(*) from Event_Schedule where E_id = ?",(event,))
        t = cur.fetchall()[0][0]
        cur.execute("select No_of_Schedules from Event where E_Id = ?",(event,))
        r = cur.fetchall()[0][0]
        if t>=r:
            return ""
        cur.execute("select ES_Id from Event_Schedule")
        r = cur.fetchall()
        gen_id = random.randint(1,1000)
        while(1):
            if len(r) == 0:
                break
            flag = 0
            for i in r:
                if i[0] == gen_id:
                    flag = 1
                    break
                else:
                    pass
            if flag == 1:
                gen_id = random.randint(1,1000)
            else:
                break
        try:
            cur.execute('insert into Event_Schedule values(?,?,?,?,?,?,?)',(gen_id,event,p_name,part,h_name,a_req,stat,))
            con.commit()
            con.close()
            return str(gen_id)
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return ""
    
# @app.route("/B_dash")
# def b_dash():
#     con = sqlite3.connect(db_path)
#     cur = con.cursor()
#     cur.execute("SELECT * FROM Budget")
#     budget_data = cur.fetchall()
#     cur.execute("SELECT * FROM Sponsor")
#     sponsor_data = cur.fetchall()
#     cur.execute("SELECT * FROM Event")
#     event_data = cur.fetchall()
#     con.close()
    
#     return render_template("B_Dash.html",budget_data=budget_data, sponsor_data=sponsor_data,event_data=event_data)

@app.route("/B_dash")
def b_dash():
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row 
    cur = con.cursor()

    cur.execute("""
        SELECT b.*, e.Name as EventName 
        FROM Budget b
        LEFT JOIN Event e ON b.E_Id = e.E_Id
    """)
    budget_data = cur.fetchall()
    
    cur.execute("""
        SELECT s.*, e.Name as EventName 
        FROM Sponsor s
        LEFT JOIN Event e ON s.E_Id = e.E_Id
        ORDER BY s.E_Id
    """)
    sponsor_data = cur.fetchall()
    
    cur.execute("""
        SELECT e.* 
        FROM Event e
        LEFT JOIN Budget b ON e.E_Id = b.E_Id
        WHERE b.E_Id IS NULL
    """)
    events_without_budget = cur.fetchall()
    
    con.close()
    
    return render_template("B_Dash.html", 
                           budget_data=budget_data, 
                           sponsor_data=sponsor_data, 
                           events_without_budget=events_without_budget)    

@app.route("/B_create",methods=m)
def b_create():
    if request.method == "GET":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event")
        r = cur.fetchall()
        return render_template("B_Create.html",options=r)
    else:
        event = int(request.form.get("event"))
        a_req = int(request.form.get("a_req"))
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select B_Id from Budget")
        r = cur.fetchall()
        gen_id = random.randint(1,1000)
        while(1):
            if len(r) == 0:
                break
            flag = 0
            for i in r:
                if i[0] == gen_id:
                    flag = 1
                    break
                else:
                    pass
            if flag == 1:
                gen_id = random.randint(1,1000)
            else:
                break
        try:
            cur.execute('insert into Budget values(?,?,?)',(gen_id,event,a_req,))
            con.commit()
            con.close()
            return str(gen_id)
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return ""

@app.route("/S_register",methods=m)
def s_register():
    if request.method == "GET":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event")
        r = cur.fetchall()
        return render_template("S_register.html",options=r)
    else:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        name = request.form.get("name")
        fund = int(request.form.get("fund"))
        c_name = request.form.get("c_name")
        event = int(request.form.get("event"))
        cur.execute("select * from Sponsor where Name = ? and Fund = ? and Company_Name = ? and E_id = ?",(name,fund,c_name,event,))
        r = cur.fetchall()
        if len(r) > 0:
            return render_template("index.html",variable="1")
        
        cur.execute("select S_Id from Sponsor")
        r = cur.fetchall()
        gen_id = random.randint(1,1000)
        while(1):
            if len(r) == 0:
                break
            flag = 0
            for i in r:
                if i[0] == gen_id:
                    flag = 1
                    break
                else:
                    pass
            if flag == 1:
                gen_id = random.randint(1,1000)
            else:
                break
        session["s_id"] = gen_id
        session["name"] = name
        session["fund"] = fund
        session["c_name"] = c_name
        session["event"] = event
        return redirect('/S_Payment')

@app.route("/S_Fund",methods=m)
def s_fund():
    if request.method == "GET":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event")
        r = cur.fetchall()
        return render_template("S_Fund.html",options=r)
    else:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        name = request.form.get("name")
        fund = int(request.form.get("fund"))
        c_name = request.form.get("c_name")
        event = int(request.form.get("event"))
        cur.execute("select S_Id from Sponsor where E_Id = ? and Name = ? and Company_Name = ?",(event,name,c_name,))
        r = cur.fetchall()
        if len(r) == 0:
            return render_template("index.html",variable="1")
        gen_id = r[0][0]
        session["s_id"] = gen_id
        session["name"] = name
        session["fund"] = fund
        session["c_name"] = c_name
        session["event"] = event
        session["mod"] = 1
        return redirect('/S_Payment')
        
    
@app.route("/S_Refund",methods=m)
def s_refund():
    if request.method == "GET":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event")
        r = cur.fetchall()
        return render_template("S_Refund.html",options=r)
    else:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        name = request.form.get("name")
        fund = int(request.form.get("fund"))
        c_name = request.form.get("c_name")
        event = int(request.form.get("event"))
        cur.execute("select S_Id from Sponsor where E_Id = ? and Name = ? and Company_Name = ?",(event,name,c_name,))
        r = cur.fetchall()
        if len(r) == 0:
            return render_template("index.html",variable="1")
        gen_id = r[0][0]
        session["s_id"] = gen_id
        session["name"] = name
        session["fund"] = fund
        session["c_name"] = c_name
        session["event"] = event
        session["mod"] = 2
        return redirect('/S_Payment')

@app.route("/A_register",methods=m)
def a_register():
    if request.method == "GET":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select * from Event")
        r = cur.fetchall()
        return render_template("A_register.html",options=r)
    else:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        name = request.form.get("name")
        phone = int(request.form.get("phone"))
        email = request.form.get("email")
        event = int(request.form.get("event"))
        spec = request.form.get("spec")
        cur.execute("select * from Attendee where E_Id = ? and Name = ? and Specialization = ? and Phone_No = ? and E_Mail = ?",(event,name,spec,phone,email,))
        r = cur.fetchall()
        if len(r) > 0:
            return render_template("index.html",variable="1")
        cur.execute("select A_Id from Attendee")
        r = cur.fetchall()
        gen_id = random.randint(1,1000)
        while(1):
            if len(r) == 0:
                break
            flag = 0
            for i in r:
                if i[0] == gen_id:
                    flag = 1
                    break
                else:
                    pass
            if flag == 1:
                gen_id = random.randint(1,1000)
            else:
                break
        session["a_id"] = gen_id
        session["name"] = name
        session["phone"] = phone
        session["spec"] = spec
        session["event"] = event
        session["email"] = email
        if spec == "guest":
            cur.execute('insert into Attendee values(?,?,?,?,?,?)',(gen_id,event,name,spec,phone,email,))
            con.commit()
            con.close()
            return render_template("index.html",variable="2")
        return redirect('/P_Payment')
        
    
@app.route("/Ticket")
def ticket():
    try:
        L = ["a_id","name","phone","spec","event","email"]
        for i in L:
            if session[i] is None:
                return render_template("index.html",variable="3")
        
        output = io.BytesIO()
        for i in L:
            output.write(f"{session[i]}\n".encode())
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/plain',
            download_name='ticket.txt',
            as_attachment=True
        )
    except Exception as e:
        print(e)
        session["error"] = e
        return redirect("/error")

@app.route("/S_Payment",methods=m)
def payment():
    if request.method == "GET":
        return render_template("Portal.html")
    else:
        b_id = int(request.form.get("b_id"))
        pin = int(request.form.get("pin"))
        gen_id = session.get("s_id")
        name = session.get("name")
        fund = session.get("fund")
        c_name = session.get("c_name")
        event = session.get("event")
        mod = session.get("mod")
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select Bank_id from Bank where Bank_id=?",(b_id,))
        r = cur.fetchall()
        if len(r) == 0:
            return render_template("index.html",variable="1")
        cur.execute("select Total_Amount from Bank where Bank_id = ? and PIN = ?",(b_id,pin,))
        r = cur.fetchall()
        if len(r) == 0:
            return render_template("index.html",variable="1")
        t_amount = int(r[0][0])
        if(fund > t_amount):
            return render_template("index.html",variable="1")
        amount = t_amount - fund
        try:
            if mod is None:
                cur.execute("update Bank set Total_Amount = ? where Bank_id = ?",(amount,b_id,))
                con.commit()
            else:
                cur.execute("update Bank set Total_Amount = Total_Amount + ? where Bank_id = ?",(fund,b_id,))
                con.commit()
            if mod is None:
                cur.execute('insert into Sponsor values(?,?,?,?,?)',(gen_id,event,name,fund,c_name,))
                con.commit()
            elif mod == 2:
                cur.execute("select Fund from Sponsor where S_Id = ?",(gen_id,))
                t = cur.fetchall()[0][0]
                if fund > t:
                    return render_template("index.html",variable="1")
                cur.execute('update Sponsor set Fund = Fund - ? where S_Id = ?',(fund,gen_id,))
                con.commit()
            else:
                cur.execute('update Sponsor set Fund = Fund + ? where S_Id = ?',(fund,gen_id,))
                con.commit()
            con.close()
            o_id = session["o_id"]
            session.clear()
            session["o_id"] = o_id
            return render_template("index.html",variable="2")
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return render_template("index.html",variable="1")

@app.route("/P_Payment",methods=m)
def p_payment():
    if request.method == "GET":
        return render_template("P_Portal.html")
    else:
        b_id = int(request.form.get("b_id"))
        pin = int(request.form.get("pin"))
        gen_id = session.get("a_id")
        name = session.get("name")
        phone = session.get("phone")
        spec = session.get("spec")
        event = session.get("event")
        email = session.get("email")
        if spec == "participant":
            fund = 10
        else:
            fund = 100
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select Bank_id from Bank where Bank_id=?",(b_id,))
        r = cur.fetchall()
        if len(r) == 0:
            return render_template("index.html",variable="1")
        cur.execute("select Total_Amount from Bank where Bank_id = ? and PIN = ?",(b_id,pin,))
        r = cur.fetchall()
        if len(r) == 0:
            return render_template("index.html",variable="1")
        t_amount = int(r[0][0])
        if(fund > t_amount):
            return render_template("index.html",variable="1")
        amount = t_amount - fund
        try:
            cur.execute("update Bank set Total_Amount = ? where Bank_id = ?",(amount,b_id,))
            con.commit()
            cur.execute('insert into Attendee values(?,?,?,?,?,?)',(gen_id,event,name,spec,phone,email,))
            con.commit()
            con.close()
            return render_template("index.html",variable="2")
        except Exception as e:
            print("Error:-",type(e).__name__)
            con.close()
            return render_template("index.html",variable="1")
        
            
if __name__ == '__main__':
    app.run(debug=True)