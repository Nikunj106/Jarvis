import tkinter as tk
import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import os
import psutil
import random
import requests
import wikipedia
import math
import re
import mysql.connector
from googleapiclient.discovery import build
from PIL import Image, ImageTk, ImageSequence

# ---------------- MYSQL SETUP -----------------
db = mysql.connector.connect(host="localhost",user="root",password="n160602008",)
cursor = db.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS jarvis_db")
cursor.execute("USE jarvis_db")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    command TEXT,
    response TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP )
    """)

def log_to_db(cmd, response):
    cursor.execute("INSERT INTO logs (command, response) VALUES (%s, %s)", (cmd, response))
    db.commit()
        
# ---------------- CONFIG -----------------
WAKE = "jarvis"
CITY = "Delhi"
YT_KEY = "AIzaSyC7zaDLebk3JUrEZX_59wy_I8LxaqG2yMk"
W_KEY = "b4e31a4aae687d2ec2e54e9083d176d3"

r, eng = sr.Recognizer(), pyttsx3.init();
eng.setProperty('rate', 180)
stop, listening, awaiting_wiki = None, False, False

# ---------------- SPEAK FUNCTION -----------------
def speak(text):
    eng.say(text)
    eng.runAndWait()
    return text  # return response so it can be stored

def greet():
    h = datetime.datetime.now().hour
    greet_time = "morning" if h < 12 else "afternoon" if h < 18 else "evening"
    speak(f"Good {greet_time}! I am Jarvis. Say Jarvis to wake me up.")

# ---------------- ACTIONS -----------------
def play_youtube(q):
    try:
        vid = build("youtube", "v3", developerKey=YT_KEY).search().list(
            q=q, part="snippet", maxResults=1, type="video").execute()['items'][0]['id']['videoId']
        webbrowser.open(f"https://youtu.be/{vid}")
        return speak(f"Playing {q}")
    except:
        return speak("YouTube error.")

def joke():
    return speak(random.choice([
        "Atoms make up everything!",
        "Fake pasta is Impasta!",
        "The scarecrow was outstanding in his field!"
    ]))

def weather():
    try:
        d = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={W_KEY}&units=metric"
        ).json()
        return speak(f"{CITY} is {d['main']['temp']}°C with {d['weather'][0]['description']}")
    except:
        return speak("Weather unavailable.")

def wiki_summary(topic):
    try:
        return speak(wikipedia.summary(topic, 2))
    except:
        return speak("Couldn't find info.")

def calculate(exp):
    exp = (exp.replace("x","*").replace("into","*").replace("times","*")
               .replace("plus","+").replace("minus","-")
               .replace("divided by","/").replace("power","**"))
    try:
        result = eval(exp, {'__builtins__': None}, math.__dict__ | {'abs': abs})
        return speak(f"Result is {result}")
    except:
        return speak("Can't calculate that.")

def system_status():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return speak(f"CPU at {cpu} percent and RAM usage at {ram} percent.")

# ---------------- COMMAND HANDLER -----------------
def handle(cmd):
    global stop, awaiting_wiki
    response = ""
    
    if any(x in cmd for x in ["hello", "hi", "hey"]):
        response = speak("Hello! How are you?")
    elif "how are you" in cmd:
        response = speak("I am just a program, but I am doing amazing!")
    elif "boss is here" in cmd:
        respose = speak(" Hi Boss Nikunj!")
    else:
        if "open notepad" in cmd:
            os.system("start notepad")
            response = speak("Opening Notepad")

        elif "open calculator" in cmd:
            os.system("start calc")
            response = speak("Opening Calculator")

        elif "open google" in cmd:
            webbrowser.open("https://google.com")
            response = speak("Opening Google")

        elif "open youtube" in cmd:
            webbrowser.open("https://youtube.com")
            response = speak("Opening YouTube")

        elif "time" in cmd:
            response = speak(datetime.datetime.now().strftime("It's %H:%M"))

        elif "system status" in cmd or "status" in cmd:
            response = system_status()

        elif "joke" in cmd:
            response = joke()

        elif "weather" in cmd:
            response = weather()

        elif "play" in cmd:
            response = play_youtube(cmd.replace("play", "").strip())

        elif "calculate" in cmd or re.search(r"\d.*[\+\-\*/]", cmd):
            response = calculate(cmd.replace("calculate", ""))

        elif any(x in cmd for x in ["tell me about", "who is", "what is"]):
            topic = re.sub("tell me about|who is|what is", "", cmd).strip()
            response = wiki_summary(topic) if topic else speak("Tell me the topic.")

        elif any(x in cmd for x in ["exit", "stop", "bye", "close"]):
            response = speak("Goodbye!")
            stop and stop(wait_for_stop=False)
            root.after(500, root.destroy)

        else:
            response = speak("I didn't understand that.")

    log_to_db(cmd, response)  # <-- Logs only executed commands & responses

# ---------------- CALLBACK -----------------
def callback(rec, audio):
    global listening, awaiting_wiki
    try:
        q = r.recognize_google(audio, language="en-IN").lower()
        print("Heard:", q)

        if awaiting_wiki:
            awaiting_wiki = False
            handle(q)

        elif listening:
            listening = False
            handle(q)

        elif WAKE in q:
            speak("Yes?")
            listening = True

    except:
        pass

# ---------------- LISTENING -----------------
def start_listening():
    global stop
    with sr.Microphone() as mic:
        r.adjust_for_ambient_noise(mic)
    stop = r.listen_in_background(sr.Microphone(), callback)

# ---------------- GUI -----------------
root = tk.Tk()
root.title("Jarvis")
root.geometry("700x550+300+100")
root.configure(bg="black")

lbl = tk.Label(root, bg="black")
lbl.pack(expand=True)

try:
    frames = [ImageTk.PhotoImage(f.copy().convert("RGBA")) for f in ImageSequence.Iterator(Image.open("mic.gif"))]
    def anim(c=0):
        lbl.config(image=frames[c])
        root.after(100, lambda: anim((c+1) % len(frames)))
    anim()
except:
    lbl.config(text="Mic Icon", fg="white")

# ---------------- START -----------------
root.after(1000, greet)
root.after(2000, start_listening)
root.mainloop()