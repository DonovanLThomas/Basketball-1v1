from flask import Flask, request, render_template
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import spacy
from datetime import datetime, timedelta
from urllib.parse import urlencode
import os
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

nlp = spacy.load("en_core_web_sm")

my_free_times = {
    "monday": ["5pm", "6pm"],
    "tuesday": ["9am", "10am", "2pm", "3pm", "4pm"],
    "wednesday": ["5pm", "6pm"],
    "thursday": ["9am", "10am", "2pm", "3pm", "4pm"],
    "friday": ["5pm", "6pm"],
    "saturday": ["10am", "11am", "12am", "1pm", "2pm", "3pm", "4pm"],
    "sunday": ["10am", "11am", "12am", "1pm", "2pm", "3pm", "4pm"]
}

signups = []
user_state = {}  # maps phone numbers to last proposed day/time

Twilio_phone_number = os.getenv("TWILIO_PHONE")
Account_SID = os.getenv("TWILIO_ACCOUNT_SID")
Auth_Token = os.getenv("TWILIO_AUTH_TOKEN")

client = Client(Account_SID, Auth_Token)

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
    return datetime.combine(next_day.date(), time_obj)

def generate_calendar_link(event_title, date_str, time_str, duration_minutes, location=""):
    dt = get_weekday(date_str, time_str)
    start = dt.strftime("%Y%m%dT%H%M%S")
    end = (dt + timedelta(minutes=duration_minutes)).strftime("%Y%m%dT%H%M%S")

    params = {
        "action": "TEMPLATE",
        "text": event_title,
        "dates": f"{start}/{end}",
        "location": location,
        "details": "1v1 Basketball Game"
    }
    return f"https://calendar.google.com/calendar/render?{urlencode(params)}"

def parse_availability_nlp(message):
    doc = nlp(message)
    days = []
    for token in doc:
        if token.text.lower() in my_free_times:
            days.append(token.text.lower())

    if "tomorrow" in message.lower():
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%A").lower()
        days.append(tomorrow)
    if "weekend" in message.lower():
        days.extend(["saturday", "sunday"])

    return days

def smart_bot_reply(user_message, phone):
    if phone in user_state:
        day, options = user_state[phone]
        for t in options:
            if t in user_message.lower():
                calendar_url = generate_calendar_link("1v1 Donovan in Basketball", day, t, 30, "EAST FIELD OUTDOOR BASKETBALL COURTS")
                del user_state[phone]
                return f"Game set for {day} at {t}. Add to your calendar: {calendar_url}"
        return f"That time doesn't match the schedule. Pick one of these: {', '.join(options)}"

    days = parse_availability_nlp(user_message)
    for day in days:
        if day in my_free_times:
            times = my_free_times[day]
            user_state[phone] = (day.capitalize(), times)
            return f"Donovan's free on {day.capitalize()}. Which of these times works for you? {', '.join(times)}"

    return "Sorry, I couldn't find a day you're free. What day works for you?"

@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name")
    phone = request.form.get("phone")

    signups.append({"name": name, "phone": phone})

    message = client.messages.create(
        body=f"Hey {name or ''}! Thanks for signing up for a 1v1 Basketball game. When are you free to play?",
        from_=Twilio_phone_number,
        to=f"+1{phone}"
    )

    return "Signup complete! Check your phone for a message."

@app.route("/sms", methods=['POST'])
def sms_reply():
    incoming_msg = request.form.get('Body')
    from_number = request.form.get('From')
    reply = smart_bot_reply(incoming_msg, from_number)

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)


if __name__ == "__main__":
    app.run(debug=True)
