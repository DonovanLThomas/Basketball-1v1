from flask import Flask, request, render_template
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
CORS(app)

Twilio_phone_number = os.getenv("TWILIO_PHONE")
Account_SID = os.getenv("TWILIO_ACCOUNT_SID")
Auth_Token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(Account_SID, Auth_Token)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

signups = []
my_free_times = {
    "modnay": ["6pm", "7pm"],
    "tuesday": ["10am", "11am", "2pm", "3pm", "4pm"],
    "wednesday": ["6pm", "7pm"],
    "thursday": ["10am", "11am", "2pm", "3pm", "4pm"],
    "friday": ["11am", "12pm", "1pm", "2pm", "3pm", "4pm", "5pm"],
    "saturday": ["10am", "11am", "12am", "1pm", "2pm", "3pm", "4pm"],
    "sunday": ["10am", "11am", "12am", "1pm", "2pm", "3pm", "4pm"]
}

def format_schedule_for_prompt(schedule_dict):
    lines = []
    for day, times in schedule_dict.items():
        line = f"{day.capitalize()}: {', '.join(times)}"
        lines.append(line)
    return "\n".join(lines)


@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name")
    phone = request.form.get("phone")

    if not phone:
        return "Phone number required", 400

    signups.append({"name": name, "phone": phone})

    intro_message = f"Hey {name or ''}! Thanks for signing up for a 1v1 Basketball game. When are you free to play?"
    client.messages.create(
        body=intro_message,
        from_=Twilio_phone_number,
        to=f"+1{phone}"
    )

    return "Signup complete! Check your phone for a message."

@app.route("/sms", methods=["POST"])
def sms_reply():
    incoming_msg = request.form.get("Body")
    from_number = request.form.get("From")

    try:
        schedule_text = format_schedule_for_prompt(my_free_times)
        # Ask Gemini for a reply
        prompt = f"""You are a basketball scheduling assistant.

        Here is my available times:
        {schedule_text}

        Help the user pick a time based on their message: "{incoming_msg}".

        List my times so they can match their schedule.

        Help them decide on a time that works for them and me. If they ask a vauge question ask a clarifying question. Keep your messages not pretty consise.

        If a question if off topic redirect them back towards the goal.
       
        Respond conversationally and ask follow-up questions if needed.
        
        Your final goal is to confirm a set time for the 1v1 basketball match.
        """
        
        response = model.generate_content([prompt])
        reply_text = response.text.strip()

    except Exception as e:
        print("Gemini API Error:", e)
        reply_text = "Sorry, I'm having trouble responding right now."

    # Send response back to user
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)