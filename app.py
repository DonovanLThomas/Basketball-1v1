from flask import Flask, request, render_template, redirect, url_for
from twilio.rest import Client
import json
import spacy 
from datetime import datetime, timedelta
from urllib.parse import urlencode
import os
from dotenv import load_dotenv 

load_dotenv()

def get_weekday(day_str, time_str):
    day_str = day_str.strip().capitalize()
    time_str = time_str.strip().replace(" ", "").upper()

    target_weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day_str)
    now = datetime.now()
    today_weekday = now.weekday()

    days_ahead = (target_weekday - today_weekday + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    
    next_day = now + timedelta(days=days_ahead)

    time_obj = datetime.strptime(time_str, "%I%p").time()
    combined = datetime.combine(next_day.date(), time_obj)

    return combined

def generate_calendar_link(event_title, date_str, time_str, duration_minutes, location=""):
    

    try:
        dt = get_weekday(date_str,time_str)
    except:
        raise ValueError("Make sure your response is formatted correctly time - 5pm and day is spelled out 'Monday'.")
    start = dt.strftime("%Y%m%dT%H%M%S")
    end = (dt + timedelta(minutes=duration_minutes)).strftime("%Y%m%dT%H%M%S")

    params = {
            "action": "TEMPLATE",
            "text": event_title,
            "dates": f"{start}/{end}",
            "location": location,
            "details": "1v1 Basketabll"
    }

    return f"https://calendar.google.com/calendar/render?{urlencode(params)}"
app = Flask(__name__)



nlp = spacy.load("en_core_web_sm")



my_free_times = {
    "monday": ["5pm", "6pm"],
    "tuesday": ["9am", "10am", "2pm", "3pm", "4pm"],
    "wednesday": ["5pm", "6pm"],
    "thursday": ["9am", "10am", "2pm", "3pm", "4pm"],
    "friday": ["5pm", "6pm"],
    "saturday":["10am","11am","12am","1m","2pm","3pm","4pm"],
    "sunday":["10am","11am","12am","1m","2pm","3pm","4pm"]
}

signups = []
chat_history = []
last_proposed_day = None
last_proposed_times = []

Twilio_phone_number = "+18314984456"
Account_SID = os.getenv("TWILIO_ACCOUNT_SID")
Auth_Token = os.getenv("TWILIO_AUTH_TOKEN")

client = Client(Account_SID, Auth_Token)

#Home page get from html

# @app.route("/", methods=["GET"])
# def index():
#     return render_template("signup.html")

# @app.route("/signup", methods=["POST"])
# def signup():
#     name = request.form.get("name")
#     phone = request.form.get("phone")

#     signup_data = {
#         "name": name,
#         "phone": phone
#     }

#     signups.append(signup_data)

#     with open('signups.json', 'w') as f:
#         json.dump(signups, f, indent = 4)

#     print(f"Recieved signup: Name={name}, Phone={phone}")

#     #Send later text with twilio
#     message = client.messages.create(
#         body = f"Hey {name}! Thanks for signing up for a 1v1 Basketball game! I'll text you to schedule a Basketball game soon",
#         from_= Twilio_phone_number,
#         to=f"+1{phone}"

#     )

#     return f"Thanks {name}! We'll text you at {phone} soon! "

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for('chat'))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        user_message = request.form.get("message")
        bot_reply = smart_bot_reply(user_message)

        # Save chat history
        chat_history.append(("User", user_message))
        chat_history.append(("Bot", bot_reply))
        
        return redirect(url_for('chat'))

    return render_template("chat.html", chat_history=chat_history)

def basic_parsing(message):
    message = message.lower()
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    available_days = []

    for day in days:
        if day in message:
            available_days.append(day)

    return available_days

def parse_availability_nlp(message):
    doc = nlp(message)
    days = []

    basic_days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    for token in doc:
        if token.text.lower() in basic_days:
            days.append(token.text.lower())

    if "tommorow" in message.lower():
        tommorow = (datetime.now() + timedelta(days=1)).strtftime("%A").lower()
    if "weekend" in message.lower():
        days.extend(["saturday", "sunday"])

    return days


def matching_time(user_days):
        for day in user_days:
             if day in my_free_times:
                times = my_free_times[day]
                return (day.capitalize(), times)
        return None

def smart_bot_reply(user_message):
    global last_proposed_day, last_proposed_times
    if last_proposed_day and last_proposed_times:
        for t in last_proposed_times:
            if t in user_message.lower():
                calender_url = generate_calendar_link(
                    "1v1 Donovan in Basketball",
                    str(last_proposed_day),
                    str(t),
                    30,
                    location="EAST FIELD OUTDOOR BASKETBALL COURTS"
                )
                return f"Ight bet yall are set to play at {last_proposed_day} at {t}. Here is a Google Calender Link: {calender_url}"
                

        return f"that time doesnt match his schedule could you give me a time from these times:{last_proposed_times}"

   
    

        
    available_days = parse_availability_nlp(user_message)

    if not available_days:
        return "Sorry, I didnt catch a day you are free. Could you tell me what day works?"
    
    match = matching_time(available_days)

    if match:
        day,times = match
        last_proposed_day = day
        last_proposed_times = times
        times_list = ", ".join(times)
        if (len(times_list) == 1):
            return f"Yessir Dono's free on {day}. Does {times_list} works for you?"
        else:
            return f"Yessir Dono's free on {day}. Which of these times work {times_list} works for you?"
    else:
        return f"Ahh he aint free that day. Suggest another time and I'll see if yall's schedule aligns"
    
    

if __name__ == "__main__":
    app.run(debug=True)

