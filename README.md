╔══════════════════════════════════════════════════════════╗
║              J.A.R.V.I.S — AI Desktop Assistant          ║
║             Just A Rather Very Intelligent System        ║
╚══════════════════════════════════════════════════════════╝

WHAT IS THIS?
─────────────
JARVIS is a voice-controlled AI desktop assistant that runs on your PC.
It wakes up when you clap twice, listens to your voice commands, and
handles everything from opening apps to playing music to answering
questions — all hands-free.

HOW TO RUN IT
─────────────
1. Install Python 3.10+
2. Install dependencies:
   pip install anthropic sounddevice numpy pyttsx3 SpeechRecognition
   pip install psutil requests pillow pyautogui pycaw comtypes

3. Place mic.gif in the same folder as jarvis.py (for the mic animation)
4. Run: python jarvis.py
5. Clap twice to open. Clap twice again to close.

WHAT IT DOES
────────────
► WAKE / SLEEP
  Double-clap to open all windows. Double-clap again to close.
  On first open: greets you, reads system stats and weather.
  On every re-open: just says "How can I help you?"

► OPEN APPS
  "Open Notepad" / "Open VS Code" / "Open Discord" / "Open Chrome"
  Supports 40+ apps. Tries multiple name variants automatically.

► OPEN WEBSITES
  "Open YouTube" / "Open GitHub" / "Open Gmail" / "Open Netflix"
  Opens directly as a new browser tab. 25+ sites built in.

► BROWSE & SEARCH
  "Open Chrome" then "Search how to make pasta"
  Searches Google in a new tab instantly.

► SPOTIFY (Free account)
  "Open Spotify" — launches the app
  "Play Blinding Lights" — searches and plays the song automatically
  "Pause" / "Play it" / "Resume" — play and pause
  "Next song" / "Skip" — skip to next track
  "Last one" / "Previous song" — go back to previous track

► YOUTUBE
  "Open YouTube" then "Play Shape of You"
  Finds the exact video using YouTube API and opens it directly.

► VOLUME CONTROL
  "Volume up" / "Volume down" — adjust by 10%
  "Volume up 20 percent" — adjust by exact amount
  "Set volume to 60" — set to exact level
  "Mute" — silence

► SYSTEM INFO
  "System status" — reads CPU, RAM, disk usage aloud
  Live CPU and RAM graphs visible in the right panel at all times.

► WEATHER
  "What's the weather" — reads current weather for your city

► WIKIPEDIA
  "Who was Einstein" / "What is quantum physics" / "Where is Iceland"
  Reads a quick 2-sentence summary from Wikipedia.

► AI QUESTIONS
  Ask anything — "Explain black holes", "What is the capital of Brazil"
  Powered by Claude AI for intelligent answers.

► KEYBOARD CONTROL
  "Copy" / "Paste" / "Cut" / "Undo" / "Redo" / "Save"
  "New tab" / "Close tab" / "Close this" (Alt+F4) / "Screenshot"
  "Refresh" / "Zoom in" / "Zoom out" / "Select all"
  Works in any app that has focus.

► DICTATION
  "Type Hello Nikunj" or "Write Dear Sir" — types text wherever
  your cursor is placed.

► REMINDERS & TIMERS
  "Remind me in 10 minutes to drink water"
  "Set a timer for 5 minutes"
  JARVIS speaks the reminder when time is up.

THREE WINDOWS
─────────────
LEFT   — Main JARVIS panel: status, conversation log, controls
CENTRE — Animated mic GIF showing JARVIS is listening
RIGHT  — Live CPU and RAM graphs (updates every second)

WHY IT'S FUN
────────────
You never touch your keyboard for routine tasks. Open apps, play songs,
search the web, control volume, take screenshots, set reminders — all by
just talking. It feels like having an actual assistant on your desktop.
The clap-to-wake mechanic makes it feel straight out of Iron Man.
