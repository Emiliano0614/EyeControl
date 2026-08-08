# EyeControl

Hands-free browser control using only eye movement and blinks. Built for people who can't use a mouse or keyboard — navigate the web with gaze and a blink instead of a click.

## What it does

EyeControl watches your face through a webcam and turns two signals into full browser control:

- **Head tilt (pitch)** → continuous scrolling. Tilt down to scroll down, tilt up to scroll up, level head = not scrolling.
- **Gaze direction (left/right) + a blink** → everything else. Blinking while looking left or right drills through a menu, one binary choice at a time, until you reach the action you want.

No mouse. No keyboard. No voice.

## How it works

The system is two parts that talk to each other over a local WebSocket:

**`backend/`** — the "brain," in Python. Runs MediaPipe face landmark detection on the webcam feed, classifies gaze into left/right zones, detects blinks, and tracks head pitch. This is where all the decision-making lives: it walks a binary drill-tree based on your zone+blink choices to figure out what you're selecting.

**`extension/`** — the "hands and eyes," a Chrome extension. Scans the current page for links and numbers them, renders the on-screen menu/overlay, and executes whatever the backend tells it to do (click a link, switch tabs, open a new tab, scroll).

### Core interaction loop

1. Head level → you're in **select mode**. Looking left or right + a blink drills one level deeper into whatever menu is currently showing (main menu, link picker, tab picker).
2. Selecting "show links" tells the extension to scan the page's DOM and number every link. That list gets sent to the backend.
3. To pick a link, you "type" its number using the same binary digit-drill-tree, one zone+blink at a time, then confirm with ENTER.
4. The backend matches the typed number against the link list and tells the extension which one to click.
5. Tilting your head at any point overrides all of this and scrolls instead — no blink detection happens while scrolling, so there's no risk of accidentally triggering a selection mid-scroll.

## Status

Early build. The gaze classification, blink detection, and digit-drill-tree logic are carried over from a proven working prototype (a standalone cursor-control practice project). What's actively being built now is the Chrome extension and the WebSocket bridge connecting it to the Python backend.

## Tech stack

- **Backend:** Python, MediaPipe (face landmark detection), OpenCV, WebSockets
- **Extension:** JavaScript (Chrome Extension APIs — content scripts, background service worker)
