from flask import Flask, request, render_templete
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import os
from dotenv import load_detenv
import google.generativeai as genai

load_detenv

app = Flask(__name__)
CORS(app)

Twilio_phone_number = os.getenv("TWILIO_PHONE")
Account_SID = os.getenv("TWILIO_ACCOUNT_SID")
Auth_Token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(Account_SID, Auth_Token)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")

signups = []

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
        # Ask Gemini for a reply
        prompt = f"""You are a basketball scheduling assistant. 
        Help the user pick a time based on their message: "{incoming_msg}".
        Respond conversationally and ask follow-up questions if needed."""
        
        response = model.generate_content(prompt)
        reply_text = response.text.strip()

    except Exception as e:
        reply_text = "Sorry, I'm having trouble responding right now."

    # Send response back to user
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)