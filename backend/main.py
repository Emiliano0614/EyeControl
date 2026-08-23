import threading
import time
import asyncio
import tkinter as tk
from backend.engine.camera_thread import run_camera
from backend.engine.zone_classifier import ZoneClassifier
from backend.engine.state_machine import CursorStateMachine
from backend.engine.cursor_window import CursorWindow
from backend import server

shared_data = {
    "t_x": 0,
    "t_y": 0,
    "pitch_signal": 0,
    "eye_openness": 0,
    "blink_detected": False,
    "running": True,
}

camera_thread = threading.Thread(target=run_camera, args=(shared_data,), daemon=True)
camera_thread.start()

print("Establishing pitch baseline — look straight at the screen...")

time.sleep(3)

baseline_samples = []
sample_start = time.time()
while time.time() - sample_start < 2.0:
    baseline_samples.append(shared_data["pitch_signal"])
    time.sleep(0.1)
pitch_baseline = sum(baseline_samples) / len(baseline_samples)
sample_spread = max(baseline_samples) - min(baseline_samples)
print(f"Baseline pitch_signal: {pitch_baseline} (averaged over {len(baseline_samples)} samples, "
      f"spread {sample_spread:.3f} — should be small, comparable to pitch's normal noise floor ~0.05-0.1)")

zc = ZoneClassifier(calibration_dir="backend/calibration")
print("Zone centroids:", zc.zone_centroids)
print("stdev — gx:", zc.std_gx)

# CHANGED: was CursorStateMachine(pitch_baseline=pitch_baseline, scroll_delta=0.25) —
# scroll_delta split into separate down/up thresholds since a single
# shared value forced an uncomfortable, straining tilt to trigger
# scroll-up. 0.15 for up was chosen to match a comfortable tilt range;
# down stays at the original 0.25.
sm = CursorStateMachine(pitch_baseline=pitch_baseline, scroll_delta_down=0.25, scroll_delta_up=0.15)

server_thread = threading.Thread(
    target=server.run_server_thread,
    args=(shared_data, sm),
    daemon=True
)
server_thread.start()

root = tk.Tk()
root.title("EyeControl Launcher")

def open_cursor_window():
    window = CursorWindow(root, shared_data, zc, sm, pitch_baseline)
    window.poll()

launch_button = tk.Button(root, text="Open Drill Tree", command=open_cursor_window)
launch_button.pack(padx=20, pady=20)

root.mainloop()