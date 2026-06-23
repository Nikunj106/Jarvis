"""
JARVIS - AI Desktop Assistant
==============================
Three windows open/close together on double-clap:
  LEFT   → Main JARVIS interface      ← MAIN_W / MAIN_H
  CENTRE → Mic GIF                    ← GIF_W  / GIF_H
  RIGHT  → CPU / RAM live graph       ← GRAPH_W / GRAPH_H

To resize: edit the six size constants under "WINDOW SIZES".
To shift windows left/right: adjust main_x / gif_x / graph_x in _compute_positions().

Run: python jarvis.py
Extra deps: pip install pillow pyautogui
"""

import os
import time
import threading
import subprocess
import platform
import webbrowser
import datetime
import queue
import collections

import numpy as np
import sounddevice as sd
import pyttsx3
import speech_recognition as sr
import psutil
import requests
import anthropic
import tkinter as tk
from PIL import Image, ImageTk, ImageSequence

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    import comtypes
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# =============================================================================
# WINDOW SIZES  ← edit these to resize any window
# =============================================================================
MAIN_W,  MAIN_H  = 450, 580   # Main JARVIS panel  (left)
GIF_W,   GIF_H   = 450, 480   # Mic GIF window     (centre)
GRAPH_W, GRAPH_H = 450, 580   # CPU/RAM graph      (right)


def _compute_positions():
    """
    [gap] [MAIN] [gap] [GIF] [gap] [GRAPH] [gap]
    gap = (screen_width - total_window_width) / 4
    All windows vertically centred.
    Shift all windows: add/subtract same number from all three _x values.
    Shift one window: change only that _x value.
    """
    import tkinter as _tk
    _tmp = _tk.Tk()
    _tmp.withdraw()
    sw = _tmp.winfo_screenwidth()
    sh = _tmp.winfo_screenheight()
    _tmp.destroy()

    total_w = MAIN_W + GIF_W + GRAPH_W
    gap     = (sw - total_w) // 4

    main_x  = gap - 12                          # ← shift main left/right here
    gif_x   = gap + MAIN_W + gap               # ← shift gif left/right here
    graph_x = gap + MAIN_W + gap + GIF_W + gap # ← shift graph left/right here

    main_y  = (sh - MAIN_H)  // 2
    gif_y   = (sh - GIF_H)   // 2
    graph_y = (sh - GRAPH_H) // 2

    return (main_x, main_y), (gif_x, gif_y), (graph_x, graph_y)


_POS_MAIN, _POS_GIF, _POS_GRAPH = _compute_positions()

# =============================================================================
# CONFIGURATION
# =============================================================================
ANTHROPIC_API_KEY = "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"
WEATHER_API_KEY   = "b4e31a4aae687d2ec2e54e9083d176d3"
YOUTUBE_API_KEY   = "AIzaSyC7zaDLebk3JUrEZX_59wy_I8LxaqG2yMk"
CITY              = "Delhi"
CLAP_THRESHOLD    = 0.15
CLAP_WINDOW       = 1.2
SAMPLE_RATE       = 44100

GIF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mic.gif")

# =============================================================================
# WEBSITE MAP
# =============================================================================
WEBSITE_MAP = {
    "youtube":        "https://www.youtube.com",
    "gmail":          "https://mail.google.com",
    "github":         "https://github.com",
    "google":         "https://www.google.com",
    "facebook":       "https://www.facebook.com",
    "instagram":      "https://www.instagram.com",
    "twitter":        "https://www.twitter.com",
    "x":              "https://www.x.com",
    "reddit":         "https://www.reddit.com",
    "netflix":        "https://www.netflix.com",
    "amazon":         "https://www.amazon.in",
    "whatsapp":       "https://web.whatsapp.com",
    "linkedin":       "https://www.linkedin.com",
    "stackoverflow":  "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "wikipedia":      "https://www.wikipedia.org",
    "maps":           "https://maps.google.com",
    "google maps":    "https://maps.google.com",
    "drive":          "https://drive.google.com",
    "google drive":   "https://drive.google.com",
    "docs":           "https://docs.google.com",
    "google docs":    "https://docs.google.com",
    "sheets":         "https://sheets.google.com",
    "meet":           "https://meet.google.com",
    "chatgpt":        "https://chat.openai.com",
    "chat gpt":       "https://chat.openai.com",
    "claude":         "https://claude.ai",
    "notion":         "https://www.notion.so",
    "trello":         "https://trello.com",
    "figma":          "https://www.figma.com",
}

# =============================================================================
# APP MAP  (windows_exe, macos_app, linux_cmd)
# =============================================================================
APP_MAP = {
    "chrome":               ("chrome",          "Google Chrome",        "google-chrome"),
    "google chrome":        ("chrome",          "Google Chrome",        "google-chrome"),
    "firefox":              ("firefox",         "Firefox",              "firefox"),
    "edge":                 ("msedge",          "Microsoft Edge",       "microsoft-edge"),
    "notepad":              ("notepad",         None,                   "gedit"),
    "notepad++":            ("notepad++",       None,                   "notepadqq"),
    "vs code":              ("code",            "Visual Studio Code",   "code"),
    "vscode":               ("code",            "Visual Studio Code",   "code"),
    "visual studio code":   ("code",            "Visual Studio Code",   "code"),
    "visual studio":        ("devenv",          "Visual Studio",        None),
    "word":                 ("winword",         "Microsoft Word",       "libreoffice --writer"),
    "excel":                ("excel",           "Microsoft Excel",      "libreoffice --calc"),
    "powerpoint":           ("powerpnt",        "Microsoft PowerPoint", "libreoffice --impress"),
    "paint":                ("mspaint",         None,                   "gimp"),
    "ms paint":             ("mspaint",         None,                   "gimp"),
    "calculator":           ("calc",            "Calculator",           "gnome-calculator"),
    "task manager":         ("taskmgr",         "Activity Monitor",     "gnome-system-monitor"),
    "file explorer":        ("explorer",        "Finder",               "nautilus"),
    "explorer":             ("explorer",        "Finder",               "nautilus"),
    "spotify":              ("spotify",         "Spotify",              "spotify"),
    "discord":              ("discord",         "Discord",              "discord"),
    "zoom":                 ("zoom",            "zoom.us",              "zoom"),
    "teams":                ("teams",           "Microsoft Teams",      "teams"),
    "microsoft teams":      ("teams",           "Microsoft Teams",      "teams"),
    "slack":                ("slack",           "Slack",                "slack"),
    "vlc":                  ("vlc",             "VLC",                  "vlc"),
    "obs":                  ("obs64",           "OBS",                  "obs"),
    "obs studio":           ("obs64",           "OBS",                  "obs"),
    "steam":                ("steam",           "Steam",                "steam"),
    "cmd":                  ("cmd",             None,                   "bash"),
    "command prompt":       ("cmd",             None,                   "bash"),
    "terminal":             ("cmd",             "Terminal",             "gnome-terminal"),
    "powershell":           ("powershell",      None,                   "bash"),
    "blender":              ("blender",         "Blender",              "blender"),
    "photoshop":            ("photoshop",       "Adobe Photoshop",      None),
    "premiere":             ("premiere",        "Adobe Premiere Pro",   None),
    "after effects":        ("afterfx",         "Adobe After Effects",  None),
    "illustrator":          ("illustrator",     "Adobe Illustrator",    None),
    "postman":              ("postman",         "Postman",              "postman"),
    "android studio":       ("studio64",        "Android Studio",       "android-studio"),
    "pycharm":              ("pycharm64",       "PyCharm",              "pycharm"),
    "intellij":             ("idea64",          "IntelliJ IDEA",        "intellij-idea"),
    "settings":             ("ms-settings:",    "System Preferences",   "gnome-control-center"),
    "windows settings":     ("ms-settings:",    "System Preferences",   "gnome-control-center"),
    "control panel":        ("control",         "System Preferences",   "gnome-control-center"),
    "snipping tool":        ("snippingtool",    "Screenshot",           "gnome-screenshot"),
    "wordpad":              ("wordpad",         None,                   "abiword"),
    "scratch":              ("scratch",         "Scratch",              "scratch"),
    "3utools":              ("3uTools",         None,                   None),
    "whatsapp":             ("whatsapp",        "WhatsApp",             None),
    "telegram":             ("telegram",        "Telegram",             "telegram-desktop"),
}

# =============================================================================
# TTS ENGINE  — single dedicated worker thread owns the engine exclusively.
# All other threads call speak() which puts work on a queue and BLOCKS until
# the worker finishes. This eliminates "run loop already started" completely.
# =============================================================================
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 178)
_tts_queue: queue.Queue = queue.Queue()


def _tts_worker():
    while True:
        text, done = _tts_queue.get()
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception as e:
            print(f"[TTS] {e}")
        finally:
            done.set()


threading.Thread(target=_tts_worker, daemon=True, name="TTS-worker").start()


def speak(text: str, status_cb=None):
    """Thread-safe speak. Queues text to the TTS worker and waits for it to finish."""
    if status_cb:
        status_cb(text)
    done = threading.Event()
    _tts_queue.put((text, done))
    done.wait()


def speak_continuous(lines: list, status_cb=None):
    """Speak multiple lines sequentially with no gap between them."""
    for line in lines:
        speak(line, status_cb)


# =============================================================================
# SYSTEM STATS
# =============================================================================
def get_system_stats() -> dict:
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    stats = {
        "cpu":  f"{cpu:.0f}%",
        "ram":  f"{ram.percent:.0f}% ({ram.used // 1024**3}GB / {ram.total // 1024**3}GB)",
        "disk": f"{disk.percent:.0f}% used ({disk.free // 1024**3}GB free)",
    }
    if GPU_AVAILABLE:
        gpus = GPUtil.getGPUs()
        if gpus:
            g = gpus[0]
            stats["gpu"] = (
                f"{g.name}, load {g.load*100:.0f}%, "
                f"memory {g.memoryUsed:.0f} of {g.memoryTotal:.0f} MB"
            )
    return stats


# =============================================================================
# WEATHER
# =============================================================================
def get_weather() -> str:
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={CITY}&appid={WEATHER_API_KEY}&units=metric"
        )
        r = requests.get(url, timeout=5)
        d = r.json()
        if r.status_code == 200:
            desc  = d["weather"][0]["description"].capitalize()
            temp  = d["main"]["temp"]
            feels = d["main"]["feels_like"]
            return f"{desc}, {temp:.0f} degrees Celsius, feels like {feels:.0f}"
        return "weather data unavailable"
    except Exception:
        return "weather data unavailable"


# =============================================================================
# YOUTUBE SEARCH  — uses YouTube Data API v3
# =============================================================================
def youtube_search(query: str) -> str | None:
    """Return the watch URL of the top result for query, or None on failure."""
    try:
        url = (
            "https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&q={requests.utils.quote(query)}"
            f"&type=video&maxResults=1&key={YOUTUBE_API_KEY}"
        )
        r = requests.get(url, timeout=5)
        d = r.json()
        items = d.get("items", [])
        if items:
            vid_id = items[0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={vid_id}"
        return None
    except Exception:
        return None


# =============================================================================
# SPOTIFY KEYBOARD AUTOMATION  (Free account workaround)
# Requires pyautogui.  Spotify must already be open.
# =============================================================================
def spotify_search_and_play(song: str) -> bool:
    """
    Search and play a song in an already-open Spotify window.
    Ctrl+L → clear → type → Enter (search) → Down → Enter (play first result).
    Does NOT re-launch Spotify. Caller ensures Spotify is open and focused.
    """
    if not PYAUTOGUI_AVAILABLE:
        return False
    try:
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "l")            # 1. focus search bar
        time.sleep(0.6)
        pyautogui.hotkey("ctrl", "a")            # select all existing text
        time.sleep(0.2)
        pyautogui.typewrite(song, interval=0.07) # 2. type song name
        time.sleep(0.4)
        pyautogui.press("enter")                 # 3. submit search
        time.sleep(2.0)                          # wait for results to load
        pyautogui.press("tab")                   # 4. tab to first result
        time.sleep(0.4)
        pyautogui.press("down")                  # 5. down arrow to select song
        time.sleep(0.4)
        pyautogui.press("enter")                 # 6. enter to play
        return True
    except Exception as e:
        print(f"[Spotify] {e}")
        return False


# =============================================================================
# WINDOWS APP LAUNCHER
# =============================================================================
def _win_open(name: str) -> bool:
    if name.startswith("ms-"):
        try:
            os.startfile(name)
            return True
        except Exception:
            return False

    variants = list(dict.fromkeys([
        name, name.title(), name.lower(), name.upper(),
        name[0].upper() + name[1:] if name else name,
        name.replace(" ", ""), name.replace(" ", "-"),
    ]))

    for v in variants:
        try:
            os.startfile(v)
            return True
        except Exception:
            pass
        try:
            subprocess.Popen(
                v, shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass
    return False


# =============================================================================
# WIKIPEDIA SEARCH
# =============================================================================
def wikipedia_summary(query: str) -> str:
    """Return a 2-sentence Wikipedia summary for query using the free public API."""
    try:
        # Search for the best matching page title
        search_url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={requests.utils.quote(query)}"
            "&format=json&srlimit=1"
        )
        sr = requests.get(search_url, timeout=5).json()
        results = sr.get("query", {}).get("search", [])
        if not results:
            return "I couldn't find anything on Wikipedia for that."
        title = results[0]["title"]

        # Fetch the extract for that title
        extract_url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query&prop=extracts&exsentences=2&exlimit=1"
            f"&explaintext&titles={requests.utils.quote(title)}&format=json"
        )
        er = requests.get(extract_url, timeout=5).json()
        pages = er.get("query", {}).get("pages", {})
        page  = next(iter(pages.values()))
        extract = page.get("extract", "").strip()
        if extract:
            return extract
        return f"I found a page called {title} but couldn't extract a summary."
    except Exception as e:
        return "Wikipedia is unavailable right now."


# =============================================================================
# VOLUME CONTROL  (Windows — pycaw)
# =============================================================================
def _get_volume_interface():
    if not PYCAW_AVAILABLE:
        return None
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def set_volume(level: float):
    """Set master volume. level is 0.0 to 1.0."""
    vol = _get_volume_interface()
    if vol:
        vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, level)), None)


def get_volume() -> float:
    """Return current master volume as 0.0–1.0."""
    vol = _get_volume_interface()
    if vol:
        return vol.GetMasterVolumeLevelScalar()
    return 0.5


def change_volume(delta: float):
    """Change volume by delta (e.g. +0.1 or -0.1)."""
    current = get_volume()
    set_volume(current + delta)


# =============================================================================
# REMINDER / TIMER
# =============================================================================
_reminder_speak_fn = None   # set by TaskHandler after init


def _parse_duration(text: str) -> int | None:
    """Parse '5 minutes', '30 seconds', '2 hours' → total seconds. Returns None if unparseable."""
    import re
    text = text.lower()
    total = 0
    found = False
    for value, unit in re.findall(r'(\d+)\s*(hour|minute|second|hr|min|sec)s?', text):
        v = int(value)
        if unit in ("hour", "hr"):
            total += v * 3600
        elif unit in ("minute", "min"):
            total += v * 60
        elif unit in ("second", "sec"):
            total += v
        found = True
    return total if found else None


def set_reminder(seconds: int, message: str):
    """Fire a spoken reminder after `seconds` seconds."""
    def _fire():
        time.sleep(seconds)
        if _reminder_speak_fn:
            _reminder_speak_fn(f"Master Nikunj, reminder: {message}")
    threading.Thread(target=_fire, daemon=True).start()


# =============================================================================
# CLAP DETECTOR
# =============================================================================
class ClapDetector:
    def __init__(self, callback):
        self.callback   = callback
        self._last_clap = 0.0
        self._running   = False

    def _audio_callback(self, indata, frames, time_info, status):
        volume = np.linalg.norm(indata) / np.sqrt(len(indata))
        if volume > CLAP_THRESHOLD:
            now = time.time()
            gap = now - self._last_clap
            if 0.15 < gap < CLAP_WINDOW:
                self._last_clap = 0.0
                threading.Thread(target=self.callback, daemon=True).start()
            else:
                self._last_clap = now

    def start(self):
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        with sd.InputStream(callback=self._audio_callback,
                            channels=1, samplerate=SAMPLE_RATE, blocksize=1024):
            while self._running:
                sd.sleep(100)

    def stop(self):
        self._running = False


# =============================================================================
# TASK HANDLER
# =============================================================================
class TaskHandler:
    def __init__(self, speak_fn, ui_display_fn):
        self.speak        = speak_fn
        self.display      = ui_display_fn
        self.ai           = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.chrome_open  = False
        self.spotify_open = False
        self.youtube_open = False
        # Wire the speak function for reminders/timers
        global _reminder_speak_fn
        _reminder_speak_fn = speak_fn

    # ─────────────────────────────────────────────────────────────────────────
    def handle(self, text: str):
        t = text.lower().strip()
        print(f"[CMD] {t}")

        # ── YouTube: play <video>  — checked FIRST so it wins over Spotify ────
        if self.youtube_open and t.startswith("play "):
            query = t.replace("play ", "", 1).strip()
            self._youtube_play(query)
            return

        # ── Spotify play handling ────────────────────────────────────────────
        if self.spotify_open and not self.youtube_open:
            # "play", "play it", "play that", "play this" = spacebar resume
            _bare_play = t.strip() in ("play", "play it", "play that",
                                        "play this", "play now", "play song")
            if _bare_play and PYAUTOGUI_AVAILABLE:
                pyautogui.press("space")
                self.speak("Playing.")
                return
            # "play <actual song name>" = search on Spotify
            if t.startswith("play "):
                song = t.replace("play ", "", 1).strip()
                if song and song not in ("it", "that", "this", "now", "song", "music"):
                    self._spotify_play(song)
                    return

        # ── Browser search ────────────────────────────────────────────────────
        if self.chrome_open and t.startswith("search "):
            self._browser_search(t.replace("search ", "", 1).strip())
            return

        # ── Open Chrome ───────────────────────────────────────────────────────
        if any(k in t for k in ["open chrome", "open browser",
                                 "open google chrome", "start working"]):
            self._open_chrome()
            return

        # ── Open Spotify ──────────────────────────────────────────────────────
        if any(k in t for k in ["open spotify", "play music", "music please"]):
            self._open_spotify()
            return

        # ── Open YouTube ──────────────────────────────────────────────────────
        if "open youtube" in t:
            self._open_youtube()
            return

        # ── Open <target> ─────────────────────────────────────────────────────
        if t.startswith("open "):
            target = t.replace("open ", "", 1).strip()
            if target in WEBSITE_MAP:
                self._open_url(WEBSITE_MAP[target], target)
            elif target in APP_MAP:
                self._launch_known_app(target)
            else:
                self._launch_unknown_app(target)
            return

        # ── Weather ───────────────────────────────────────────────────────────
        if "weather" in t:
            self.speak(f"Current weather: {get_weather()}")
            return

        # ── System stats ──────────────────────────────────────────────────────
        if any(k in t for k in ["system status", "system stats",
                                  "cpu", "ram", "memory", "gpu"]):
            s = get_system_stats()
            msg = (f"CPU at {s['cpu']}, RAM at {s['ram']}, disk at {s['disk']}.")
            if "gpu" in s:
                msg += f" GPU: {s['gpu']}."
            self.speak(msg)
            return

        # ── Time / date ───────────────────────────────────────────────────────
        if any(k in t for k in ["what time", "what's the time",
                                  "current time", "what date", "today's date"]):
            now = datetime.datetime.now()
            self.speak(now.strftime("It is %I:%M %p on %A, %B %d %Y"))
            return

        # ── Shutdown ──────────────────────────────────────────────────────────
        if any(k in t for k in ["shutdown", "goodbye", "exit", "quit", "bye"]):
            self.speak("Shutting down. Goodbye!")
            time.sleep(1)
            os._exit(0)

        # ── Spotify controls — keyword anywhere in sentence ─────────────────
        if self.spotify_open and PYAUTOGUI_AVAILABLE:
            if any(k in t for k in ["pause", "stop music", "stop song"]) and \
               not any(k in t for k in ["play ", "next", "previous", "skip"]):
                pyautogui.press("space")
                self.speak("Paused.")
                return
            if any(k in t for k in ["resume", "unpause", "continue music",
                                      "continue playing"]):
                pyautogui.press("space")
                self.speak("Resumed.")
                return
            if any(k in t for k in ["next song", "next track", "skip", "skip song",
                                      "next one", "play next"]):
                pyautogui.hotkey("ctrl", "right")
                self.speak("Next song.")
                return
            if any(k in t for k in ["previous song", "previous track",
                                      "last song", "last one", "previous one",
                                      "play previous", "back song", "go back"]):
                pyautogui.hotkey("ctrl", "left")
                self.speak("Going back.")
                return

        # ── Volume — keyword anywhere ─────────────────────────────────────────
        if "volume" in t or any(k in t for k in ["louder", "quieter", "mute",
                                                   "silence", "turn up", "turn down",
                                                   "shut up", "no sound"]):
            import re as _re

            # "set volume to 60" / "volume 60 percent" / "volume at 60"
            _set_match = _re.search(
                r'(?:set\s+)?volume\s+(?:to\s+|at\s+)?(\d+)', t
            )
            # "volume up 10 percent" / "turn up by 20"
            _up_match  = _re.search(
                r'(?:volume\s+up|increase\s+volume|turn\s+up|louder)\s+(?:by\s+)?(\d+)', t
            )
            _dn_match  = _re.search(
                r'(?:volume\s+down|decrease\s+volume|turn\s+down|quieter)\s+(?:by\s+)?(\d+)', t
            )

            if _set_match:
                level = int(_set_match.group(1)) / 100.0
                set_volume(level)
                time.sleep(0.15)
                pct = int(get_volume() * 100)
                self.speak(f"Volume set to {pct} percent.")
                return
            elif _up_match:
                delta = int(_up_match.group(1)) / 100.0
                change_volume(delta)
                time.sleep(0.15)
                pct = int(get_volume() * 100)
                self.speak(f"Volume at {pct} percent.")
                return
            elif _dn_match:
                delta = int(_dn_match.group(1)) / 100.0
                change_volume(-delta)
                time.sleep(0.15)
                pct = int(get_volume() * 100)
                self.speak(f"Volume at {pct} percent.")
                return
            elif any(k in t for k in ["volume up", "increase volume", "louder",
                                       "turn up", "turn it up", "volume high"]):
                change_volume(0.1)
                time.sleep(0.15)
                pct = int(get_volume() * 100)
                self.speak(f"Volume at {pct} percent.")
                return
            elif any(k in t for k in ["volume down", "decrease volume", "quieter",
                                        "turn down", "turn it down", "volume low"]):
                change_volume(-0.1)
                time.sleep(0.15)
                pct = int(get_volume() * 100)
                self.speak(f"Volume at {pct} percent.")
                return
            elif any(k in t for k in ["mute", "silence", "shut up", "no sound"]):
                set_volume(0.0)
                self.speak("Muted.")
                return

        # ── Dictation — checked BEFORE shortcuts so "write paste" types the word
        for prefix in ("write ", "type ", "dictate "):
            if t.startswith(prefix):
                dictated = text[len(prefix):]
                if PYAUTOGUI_AVAILABLE:
                    try:
                        import pyperclip
                        pyperclip.copy(dictated)
                        pyautogui.hotkey("ctrl", "v")
                    except Exception:
                        pyautogui.typewrite(dictated, interval=0.04)
                self.speak("Typed.")
                return

        # ── Keyboard shortcuts — keyword anywhere in sentence ─────────────────
        if PYAUTOGUI_AVAILABLE:
            # Order matters: more specific phrases first
            if any(k in t for k in ["select all", "select everything"]):
                pyautogui.hotkey("ctrl", "a")
                self.speak("Selected all.")
                return
            if any(k in t for k in ["copy that", "copy it", "copy this", "copy"]):
                pyautogui.hotkey("ctrl", "c")
                self.speak("Copied.")
                return
            if any(k in t for k in ["paste that", "paste it", "paste this", "paste"]):
                pyautogui.hotkey("ctrl", "v")
                self.speak("Pasted.")
                return
            if any(k in t for k in ["cut that", "cut it", "cut this", "cut"]):
                pyautogui.hotkey("ctrl", "x")
                self.speak("Cut.")
                return
            if any(k in t for k in ["undo that", "undo it", "undo this", "undo"]):
                pyautogui.hotkey("ctrl", "z")
                self.speak("Undone.")
                return
            if any(k in t for k in ["redo that", "redo it", "redo this", "redo"]):
                pyautogui.hotkey("ctrl", "y")
                self.speak("Redone.")
                return
            if any(k in t for k in ["save file", "save that", "save it", "save"]):
                pyautogui.hotkey("ctrl", "s")
                self.speak("Saved.")
                return
            if any(k in t for k in ["new tab", "open tab", "open a new tab"]):
                pyautogui.hotkey("ctrl", "t")
                self.speak("New tab.")
                return
            if any(k in t for k in ["close this", "close this window",
                                      "close the window", "close app",
                                      "close application", "close the app",
                                      "kill this", "exit this"]):
                pyautogui.hotkey("alt", "f4")
                self.speak("Closed.")
                return
            if any(k in t for k in ["close tab", "shut the tab", "close this tab",
                                      "close current tab"]):
                pyautogui.hotkey("ctrl", "w")
                self.speak("Tab closed.")
                return
            if any(k in t for k in ["go forward", "forward page"]):
                pyautogui.hotkey("alt", "right")
                self.speak("Going forward.")
                return
            if any(k in t for k in ["go back", "go backwards", "previous page"]) \
               and not self.spotify_open:
                pyautogui.hotkey("alt", "left")
                self.speak("Going back.")
                return
            if any(k in t for k in ["refresh", "reload", "refresh the page",
                                      "reload the page"]):
                pyautogui.hotkey("ctrl", "r")
                self.speak("Refreshed.")
                return
            if any(k in t for k in ["zoom in", "make it bigger"]):
                pyautogui.hotkey("ctrl", "=")
                self.speak("Zoomed in.")
                return
            if any(k in t for k in ["zoom out", "make it smaller"]):
                pyautogui.hotkey("ctrl", "-")
                self.speak("Zoomed out.")
                return
            if any(k in t for k in ["screenshot", "take a screenshot",
                                      "take screenshot", "screen capture",
                                      "capture the screen"]):
                pyautogui.hotkey("win", "shift", "s")
                self.speak("Screenshot taken.")
                return

        # ── Reminder / timer ──────────────────────────────────────────────────
        if any(k in t for k in ["remind me", "set a reminder", "reminder"]):
            import re as _re
            match = _re.search(r'remind me in (.+?) to (.+)', t)
            if match:
                secs = _parse_duration(match.group(1).strip())
                msg  = match.group(2).strip()
                if secs:
                    set_reminder(secs, msg)
                    label = f"{secs//60} minutes" if secs >= 60 else f"{secs} seconds"
                    self.speak(f"Reminder set. I'll remind you to {msg} in {label}.")
                else:
                    self.speak("I couldn't understand the time duration.")
            else:
                self.speak("Please say: remind me in 5 minutes to do something.")
            return

        if any(k in t for k in ["set a timer", "set timer", "timer for",
                                  "start timer", "start a timer"]):
            secs = _parse_duration(t)
            if secs:
                set_reminder(secs, "your timer is up!")
                label = f"{secs//60} minutes" if secs >= 60 else f"{secs} seconds"
                self.speak(f"Timer set for {label}.")
            else:
                self.speak("Please say something like: set a timer for 5 minutes.")
            return

        # ── Wikipedia — who/what/where/when/which anywhere in sentence ────────
        import re as _re
        wiki_match = _re.search(
            r'\b(who|what|where|when|which)\b.{0,8}\b(is|are|was|were)\b\s*(.+)',
            t
        )
        if wiki_match:
            query = wiki_match.group(3).strip().rstrip("?.")
            if query:
                self.display(f"Looking up: {query}...")
                self.speak(wikipedia_summary(query))
                return
        for k in ("tell me about ", "explain "):
            if k in t:
                query = t.split(k, 1)[1].strip().rstrip("?.")
                if query:
                    self.display(f"Looking up: {query}...")
                    self.speak(wikipedia_summary(query))
                    return

        # ── AI fallback ───────────────────────────────────────────────────────
        self._ask_claude(text)

    # ── Spotify ───────────────────────────────────────────────────────────────
    def _open_spotify(self):
        self.spotify_open = True
        self.youtube_open = False   # switching to Spotify context
        try:
            if platform.system() == "Windows":
                subprocess.Popen(
                    'start spotify', shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", "Spotify"])
            else:
                subprocess.Popen(["spotify"])
            self.speak(
                "Spotify is open. Just say play followed by any song name "
                "and I'll search and play it for you."
            )
        except Exception:
            self.speak("Couldn't open Spotify.")

    def _spotify_play(self, song: str):
        if not PYAUTOGUI_AVAILABLE:
            self.speak("Keyboard automation is not available. Please install pyautogui.")
            return
        self.speak(f"Playing {song} on Spotify.")
        # Bring Spotify to front first, then run keyboard automation
        def _do_play():
            if platform.system() == "Windows":
                subprocess.Popen(
                    'start spotify', shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                time.sleep(2.0)   # wait for Spotify window to gain focus
            spotify_search_and_play(song)
        threading.Thread(target=_do_play, daemon=True).start()

    # ── YouTube ───────────────────────────────────────────────────────────────
    def _open_youtube(self):
        self.youtube_open = True
        self.chrome_open  = True
        webbrowser.open_new_tab("https://www.youtube.com")
        self.speak(
            "YouTube is open. Say play followed by any video name "
            "and I'll find and play it for you."
        )

    def _youtube_play(self, query: str):
        self.speak(f"Searching YouTube for {query}.")
        url = youtube_search(query)
        if url:
            webbrowser.open_new_tab(url)
            self.speak(f"Playing {query} on YouTube.")
        else:
            # Fallback: open YouTube search page
            encoded = requests.utils.quote(query)
            webbrowser.open_new_tab(
                f"https://www.youtube.com/results?search_query={encoded}"
            )
            self.speak(f"Opened YouTube search results for {query}.")

    # ── Browser ───────────────────────────────────────────────────────────────
    def _open_chrome(self):
        self.chrome_open = True
        try:
            if platform.system() == "Windows":
                subprocess.Popen(
                    'start chrome --new-window about:newtab',
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", "Google Chrome",
                                  "--args", "--new-window"])
            else:
                subprocess.Popen(["google-chrome", "--new-window"])
        except Exception:
            webbrowser.open_new("about:newtab")
        self.speak(
            "Chrome is open. Say search followed by anything to search, "
            "or open YouTube, open GitHub, and so on."
        )

    def _open_url(self, url: str, name: str):
        self.chrome_open = True
        webbrowser.open_new_tab(url)
        self.speak(f"Opening {name}.")

    def _browser_search(self, query: str):
        encoded = requests.utils.quote(query)
        webbrowser.open_new_tab(f"https://www.google.com/search?q={encoded}")
        self.speak(f"Searching for {query}.")

    # ── Apps ──────────────────────────────────────────────────────────────────
    def _launch_known_app(self, spoken: str):
        win_exe, mac_app, linux_cmd = APP_MAP[spoken]
        if platform.system() == "Windows":
            if _win_open(win_exe):
                self.speak(f"Opening {spoken}.")
            else:
                self.speak(f"I couldn't find {spoken}. Make sure it is installed.")
        elif platform.system() == "Darwin":
            if mac_app:
                result = subprocess.run(["open", "-a", mac_app], capture_output=True)
                if result.returncode == 0:
                    self.speak(f"Opening {spoken}.")
                else:
                    self.speak(f"Couldn't find {spoken} on this Mac.")
            else:
                self.speak(f"{spoken} is not available on macOS.")
        else:
            if linux_cmd:
                try:
                    subprocess.Popen(linux_cmd.split(),
                                     stderr=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL)
                    self.speak(f"Opening {spoken}.")
                except FileNotFoundError:
                    self.speak(f"Couldn't find {spoken}. Is it installed?")
            else:
                self.speak(f"No Linux command configured for {spoken}.")

    def _launch_unknown_app(self, spoken: str):
        self.display(f"Looking for '{spoken}'…")
        if platform.system() == "Windows":
            if _win_open(spoken):
                self.speak(f"Opening {spoken}.")
            else:
                self.speak(
                    f"I couldn't find {spoken}. Please make sure it is installed."
                )
        elif platform.system() == "Darwin":
            for v in [spoken.title(), spoken, spoken.lower()]:
                result = subprocess.run(["open", "-a", v], capture_output=True)
                if result.returncode == 0:
                    self.speak(f"Opening {spoken}.")
                    return
            self.speak(f"Couldn't find {spoken} on this Mac.")
        else:
            for v in [spoken, spoken.lower(),
                      spoken.replace(" ", "-"), spoken.replace(" ", "")]:
                try:
                    subprocess.Popen([v], stderr=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL)
                    self.speak(f"Opening {spoken}.")
                    return
                except FileNotFoundError:
                    continue
            self.speak(f"Couldn't find {spoken}. Is it installed?")

    def _ask_claude(self, text: str):
        self.display("Thinking…")
        try:
            msg = self.ai.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=(
                    "You are JARVIS, a helpful AI desktop assistant for master Nikunj. "
                    "Give concise answers (2-3 sentences max) suitable for voice."
                ),
                messages=[{"role": "user", "content": text}],
            )
            self.speak(msg.content[0].text)
        except Exception:
            self.speak("I didn't quite catch that. Could you say it again?")


# =============================================================================
# VOICE LISTENER
# =============================================================================
class VoiceListener:
    def __init__(self, command_queue: queue.Queue):
        self.q       = command_queue
        self.rec     = sr.Recognizer()
        self.mic     = sr.Microphone()
        self._active = False

    def activate(self):
        self._active = True
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def deactivate(self):
        self._active = False

    def _listen_loop(self):
        with self.mic as source:
            self.rec.adjust_for_ambient_noise(source, duration=0.5)
            while self._active:
                try:
                    audio = self.rec.listen(source, timeout=5, phrase_time_limit=8)
                    text  = self.rec.recognize_google(audio)
                    self.q.put(text)
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print(f"[ASR] {e}")


# =============================================================================
# WINDOW 1 — MAIN JARVIS PANEL  (left)
# =============================================================================
class MainWindow:
    BG     = "#050e1a"
    ACCENT = "#00d4ff"
    DIM    = "#1a3a52"
    TEXT   = "#e0f7ff"
    FHD    = ("Courier New", 22, "bold")
    FLG    = ("Courier New", 13)
    FSM    = ("Courier New", 10)

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JARVIS")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        self.root.withdraw()
        self._build()
        self._position()

    def _position(self):
        x, y = _POS_MAIN
        self.root.geometry(f"{MAIN_W}x{MAIN_H}+{x}+{y}")

    def _build(self):
        r = self.root
        tk.Label(r, text="J.A.R.V.I.S", font=self.FHD,
                 fg=self.ACCENT, bg=self.BG).pack(pady=(16, 0))
        tk.Label(r, text="Just A Rather Very Intelligent System",
                 font=self.FSM, fg=self.DIM, bg=self.BG).pack()
        tk.Frame(r, bg=self.ACCENT, height=1).pack(fill="x", padx=24, pady=8)

        self.status_var = tk.StringVar(value="")
        tk.Label(r, textvariable=self.status_var, font=self.FLG,
                 fg=self.TEXT, bg=self.BG, wraplength=MAIN_W - 48,
                 justify="left").pack(padx=20, pady=4, anchor="w")

        lf = tk.Frame(r, bg=self.DIM)
        lf.pack(fill="both", expand=True, padx=20, pady=(4, 10))
        self.log = tk.Text(lf, bg=self.BG, fg=self.TEXT, font=self.FSM,
                           bd=0, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

        bot = tk.Frame(r, bg=self.BG)
        bot.pack(fill="x", padx=20, pady=(0, 10))
        self.mode_lbl = tk.Label(bot, text="● LISTENING",
                                 font=self.FSM, fg=self.ACCENT, bg=self.BG)
        self.mode_lbl.pack(side="left")
        tk.Label(bot, text="Double-clap to hide",
                 font=self.FSM, fg=self.DIM, bg=self.BG).pack(side="right")

    def show(self):
        self._position()
        self.root.deiconify()
        self.root.lift()

    def hide(self):
        self.root.withdraw()

    def set_status(self, text: str):
        self.status_var.set(text)

    def log_message(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", f"\n▶  {text}")
        self.log.see("end")
        self.log.configure(state="disabled")


# =============================================================================
# WINDOW 2 — MIC GIF  (centre)
# =============================================================================
class MicWindow:
    BG = "#050e1a"

    def __init__(self):
        self.win = tk.Toplevel()
        self.win.title("")
        self.win.configure(bg=self.BG)
        self.win.resizable(False, False)
        self.win.overrideredirect(True)
        self.win.withdraw()
        self._frames  = []
        self._delays  = []
        self._idx     = 0
        self._running = False
        self._lbl     = None
        self._build()
        self._position()
        self._load_gif()

    def _position(self):
        x, y = _POS_GIF
        self.win.geometry(f"{GIF_W}x{GIF_H}+{x}+{y}")

    def _build(self):
        self._lbl = tk.Label(self.win, bg=self.BG, bd=0)
        self._lbl.pack(fill="both", expand=True)

    def _load_gif(self):
        if not os.path.exists(GIF_PATH):
            self._lbl.configure(text="🎤", font=("Courier New", 80), fg="#00d4ff")
            return
        try:
            img = Image.open(GIF_PATH)
            for frame in ImageSequence.Iterator(img):
                f = frame.convert("RGBA").resize((GIF_W, GIF_H), Image.LANCZOS)
                self._frames.append(ImageTk.PhotoImage(f))
                d = frame.info.get("duration", 80)
                self._delays.append(max(d, 30))
        except Exception as e:
            print(f"[GIF] {e}")
            self._lbl.configure(text="🎤", font=("Courier New", 80), fg="#00d4ff")

    def _animate(self):
        if not self._running or not self._frames:
            return
        self._lbl.configure(image=self._frames[self._idx])
        delay = self._delays[self._idx]
        self._idx = (self._idx + 1) % len(self._frames)
        self.win.after(delay, self._animate)

    def show(self):
        self._position()
        self.win.deiconify()
        self.win.lift()
        self._running = True
        self._idx = 0
        self._animate()

    def hide(self):
        self._running = False
        self.win.withdraw()


# =============================================================================
# WINDOW 3 — CPU / RAM GRAPH  (right)
# =============================================================================
HISTORY = 60

class GraphWindow:
    BG        = "#050e1a"
    ACCENT    = "#00d4ff"
    DIM       = "#0a1f33"
    GRID      = "#0d2540"
    CPU_COL   = "#00d4ff"
    RAM_COL   = "#0077ff"
    TEXT_COL  = "#e0f7ff"
    LABEL_COL = "#4a8fa8"
    FSM       = ("Courier New", 9)
    FMD       = ("Courier New", 11, "bold")

    def __init__(self):
        self.win = tk.Toplevel()
        self.win.title("System Monitor")
        self.win.configure(bg=self.BG)
        self.win.resizable(False, False)
        self.win.withdraw()

        self._cpu_hist = collections.deque([0.0] * HISTORY, maxlen=HISTORY)
        self._ram_hist = collections.deque([0.0] * HISTORY, maxlen=HISTORY)
        self._running  = False
        self._build()
        self._position()

    def _position(self):
        x, y = _POS_GRAPH
        self.win.geometry(f"{GRAPH_W}x{GRAPH_H}+{x}+{y}")

    def _build(self):
        w   = self.win
        pad = 14

        tk.Label(w, text="SYSTEM MONITOR", font=self.FMD,
                 fg=self.ACCENT, bg=self.BG).pack(pady=(12, 2))
        tk.Frame(w, bg=self.ACCENT, height=1).pack(fill="x", padx=pad, pady=4)

        cpu_hdr = tk.Frame(w, bg=self.BG)
        cpu_hdr.pack(fill="x", padx=pad)
        tk.Label(cpu_hdr, text="CPU", font=self.FMD,
                 fg=self.CPU_COL, bg=self.BG).pack(side="left")
        self._cpu_pct_var = tk.StringVar(value="0%")
        tk.Label(cpu_hdr, textvariable=self._cpu_pct_var, font=self.FMD,
                 fg=self.TEXT_COL, bg=self.BG).pack(side="right")

        graph_h = int(GRAPH_H * 0.33)
        self._cpu_canvas = tk.Canvas(
            w, width=GRAPH_W - pad * 2, height=graph_h,
            bg=self.DIM, highlightthickness=0
        )
        self._cpu_canvas.pack(padx=pad, pady=(2, 6))

        tk.Frame(w, bg=self.GRID, height=1).pack(fill="x", padx=pad, pady=2)

        ram_hdr = tk.Frame(w, bg=self.BG)
        ram_hdr.pack(fill="x", padx=pad)
        tk.Label(ram_hdr, text="RAM", font=self.FMD,
                 fg=self.RAM_COL, bg=self.BG).pack(side="left")
        self._ram_pct_var = tk.StringVar(value="0%")
        tk.Label(ram_hdr, textvariable=self._ram_pct_var, font=self.FMD,
                 fg=self.TEXT_COL, bg=self.BG).pack(side="right")

        self._ram_canvas = tk.Canvas(
            w, width=GRAPH_W - pad * 2, height=graph_h,
            bg=self.DIM, highlightthickness=0
        )
        self._ram_canvas.pack(padx=pad, pady=(2, 6))

        tk.Frame(w, bg=self.ACCENT, height=1).pack(fill="x", padx=pad, pady=4)
        self._footer_var = tk.StringVar(value="")
        tk.Label(w, textvariable=self._footer_var, font=self.FSM,
                 fg=self.LABEL_COL, bg=self.BG,
                 justify="left", wraplength=GRAPH_W - pad * 2).pack(
            padx=pad, pady=(2, 10), anchor="w"
        )

    def _draw_graph(self, canvas: tk.Canvas,
                    history: collections.deque, color: str):
        canvas.delete("all")
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        for pct in (25, 50, 75):
            y = ch - int(ch * pct / 100)
            canvas.create_line(0, y, cw, y, fill=self.GRID, dash=(3, 3))
            canvas.create_text(4, y - 2, text=f"{pct}%",
                               fill=self.LABEL_COL, font=self.FSM, anchor="sw")

        pts  = list(history)
        n    = len(pts)
        if n < 2:
            return
        step = cw / (n - 1)
        coords = []
        for i, v in enumerate(pts):
            coords.extend([i * step, ch - (v / 100.0) * ch])

        canvas.create_line(*coords, fill=color, width=2, smooth=True)
        fill_coords = [0, ch] + coords + [coords[-2], ch]
        canvas.create_polygon(*fill_coords, fill=color,
                               stipple="gray25", outline="")

    def _update_loop(self):
        while self._running:
            cpu      = psutil.cpu_percent(interval=1)
            mem      = psutil.virtual_memory()
            disk     = psutil.disk_usage("/")
            self._cpu_hist.append(cpu)
            self._ram_hist.append(mem.percent)
            self._cpu_pct_var.set(f"{cpu:.0f}%")
            self._ram_pct_var.set(f"{mem.percent:.0f}%")
            self._footer_var.set(
                f"RAM  {mem.used // 1024**3}GB / {mem.total // 1024**3}GB\n"
                f"Disk  {disk.percent:.0f}% used  ({disk.free // 1024**3}GB free)"
            )
            self.win.after(0, self._redraw)
            time.sleep(1)

    def _redraw(self):
        self._draw_graph(self._cpu_canvas, self._cpu_hist, self.CPU_COL)
        self._draw_graph(self._ram_canvas, self._ram_hist, self.RAM_COL)

    def show(self):
        self._position()
        self.win.deiconify()
        self.win.lift()
        self._running = True
        threading.Thread(target=self._update_loop, daemon=True).start()

    def hide(self):
        self._running = False
        self.win.withdraw()


# =============================================================================
# JARVIS CORE
# =============================================================================
class Jarvis:
    def __init__(self):
        self.visible  = False
        self.greeted  = False
        self.cmd_q    = queue.Queue()
        self.handler  = None

        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("JARVIS-root")

        self.main_win  = MainWindow(tk.Toplevel(self._root))
        self.mic_win   = MicWindow()
        self.graph_win = GraphWindow()

        self.clap  = ClapDetector(callback=self._on_double_clap)
        self.voice = VoiceListener(self.cmd_q)

        self._root.after(300, self._boot)

    # ── Boot ──────────────────────────────────────────────────────────────────
    def _boot(self):
        def run():
            self.handler = TaskHandler(
                speak_fn=self._speak_and_log,
                ui_display_fn=self._status,
            )
            self.clap.start()
            threading.Thread(target=self._process_loop, daemon=True).start()
            print("[JARVIS] Ready — double-clap to open.")
        threading.Thread(target=run, daemon=True).start()

    # ── Double-clap ───────────────────────────────────────────────────────────
    def _on_double_clap(self):
        if not self.visible:
            self._open_all()
        else:
            self._close_all()

    def _open_all(self):
        self.visible = True
        self._root.after(0, self.main_win.show)
        self._root.after(0, self.mic_win.show)
        self._root.after(0, self.graph_win.show)

        if not self.greeted:
            self.greeted = True
            threading.Thread(target=self._full_greeting, daemon=True).start()
        else:
            self._log("How can I help you, master Nikunj?")
            speak("How can I help you, master Nikunj?", self._status)
            self.voice.activate()

    def _close_all(self):
        self.visible = False
        self.voice.deactivate()
        self._root.after(0, self.main_win.hide)
        self._root.after(0, self.mic_win.hide)
        self._root.after(0, self.graph_win.hide)
        speak("Goodbye.")

    # ── First greeting — continuous, no gaps ─────────────────────────────────
    def _full_greeting(self):
        stats   = get_system_stats()
        weather = get_weather()

        # Build stat line for the log
        stat_line = (f"CPU: {stats['cpu']}   RAM: {stats['ram']}   "
                     f"Disk: {stats['disk']}")
        if "gpu" in stats:
            stat_line += f"   GPU: {stats['gpu']}"

        # Log everything at once before speaking
        for line in [
            "Hi master Nikunj.",
            stat_line,
            f"Weather: {weather}",
            "All systems nominal. How can I help you?",
        ]:
            self._log(line)

        # Build the full speech sequence
        speech_lines = [
            "Hi master Nikunj.",
            f"Your CPU is running at {stats['cpu']},",
            f"RAM at {stats['ram']},",
            f"and disk at {stats['disk']}.",
        ]
        if "gpu" in stats:
            speech_lines.append(f"GPU: {stats['gpu']}.")

        speech_lines.append(f"Weather outside: {weather}.")
        speech_lines.append("All systems nominal. How can I help you?")

        # Speak all lines in one continuous TTS session — no gaps
        speak_continuous(speech_lines, self._status)

        self._status("Listening…")
        self.voice.activate()

    # ── Command loop ──────────────────────────────────────────────────────────
    def _process_loop(self):
        while True:
            try:
                cmd = self.cmd_q.get(timeout=1)
                if self.visible and self.handler:
                    self._log(f"You said: {cmd}")
                    self._status(f"You said: {cmd}")
                    self.handler.handle(cmd)
            except queue.Empty:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _log(self, text: str):
        self._root.after(0, lambda: self.main_win.log_message(text))

    def _status(self, text: str):
        self._root.after(0, lambda: self.main_win.set_status(text))

    def _speak_and_log(self, text: str, cb=None):
        self._log(text)
        speak(text, self._status)

    def run(self):
        self._root.mainloop()


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    jarvis = Jarvis()
    jarvis.run() 