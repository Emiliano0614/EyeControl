import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import statistics

from .gaze_math import gaze_math, eye_openness_math

model_path = 'backend/model/face_landmarker.task'

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)

landmarker = vision.FaceLandmarker.create_from_options(options)

# --- Blink detection tuning ---
# Ported from cv-practice 05, NOT re-measured on EyeControl's own
# camera/lighting yet. 05's values came from live-timed testing on
# cv-practice's setup — treated as a trusted starting point, same as
# zone_classifier.py's merge decision, but still flagged for
# re-verification here if blink timing feels off in practice.
BLINK_THRESHOLD = 0.16
BLINK_FRAMES_REQUIRED = 3
REOPEN_FRAMES_REQUIRED = 3
PITCH_FREEZE_THRESHOLD = 0.35

# --- Live smoothing buffers ---
buffer_x = []
buffer_y = []
buffer_pitch = []


def run_camera(shared_data):
    cap = cv2.VideoCapture(0)
    frame_timestamp_ms = 0
    closed_frame_count = 0
    open_frame_count = 0
    blink_armed = True  # False right after a blink fires, until reopen confirmed

    while shared_data["running"] == True:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        frame_timestamp_ms += 33
        result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

        if result.face_landmarks:
            landmarks = result.face_landmarks[0]

            nose_tip = landmarks[1]
            left_iris_center = landmarks[468]
            left_eye_outer_corner = landmarks[33]
            left_eye_inner_corner = landmarks[133]
            left_upper_eyelid = landmarks[159]
            left_lower_eyelid = landmarks[145]

            # --- eye_openness: every frame, unconditionally ---
            eye_openness = eye_openness_math(
                left_upper_eyelid, left_lower_eyelid,
                left_eye_outer_corner, left_eye_inner_corner
            )
            shared_data["eye_openness"] = eye_openness

            # --- gaze/pitch: only trusted into the smoothing buffers
            # when eye is clearly open (PITCH_FREEZE_THRESHOLD, NOT
            # BLINK_THRESHOLD — separate job, separate bar, see 05's
            # PITCH_FREEZE_THRESHOLD comment for the live-data reasoning) ---
            if eye_openness >= PITCH_FREEZE_THRESHOLD:
                gaze = gaze_math(
                    left_eye_inner_corner, left_eye_outer_corner, nose_tip,
                    left_upper_eyelid, left_lower_eyelid, left_iris_center
                )

                if len(buffer_x) >= 15:
                    buffer_x.pop(0)
                if len(buffer_y) >= 15:
                    buffer_y.pop(0)
                if len(buffer_pitch) >= 15:
                    buffer_pitch.pop(0)

                buffer_x.append(gaze["t_x"])
                buffer_y.append(gaze["t_y"])
                buffer_pitch.append(gaze["pitch_signal"])

                shared_data["t_x"] = statistics.median(buffer_x)
                shared_data["t_y"] = statistics.median(buffer_y)
                shared_data["pitch_signal"] = statistics.median(buffer_pitch)

            # --- blink counting + reopen-gate: always runs, every
            # frame, regardless of the pitch-freeze branch above ---
            if eye_openness < BLINK_THRESHOLD:
                open_frame_count = 0
                if blink_armed:
                    closed_frame_count += 1
            else:
                closed_frame_count = 0
                open_frame_count += 1
                if open_frame_count >= REOPEN_FRAMES_REQUIRED:
                    blink_armed = True

            if blink_armed and closed_frame_count == BLINK_FRAMES_REQUIRED:
                shared_data["blink_detected"] = True
                blink_armed = False
                closed_frame_count = 0

    cap.release()


if __name__ == "__main__":
    shared_data = {
        "t_x": 0,
        "t_y": 0,
        "pitch_signal": 0,
        "running": True,
        "eye_openness": 0,
        "blink_detected": False,
    }
    import threading
    import time
    camera_thread = threading.Thread(target=run_camera, args=(shared_data,), daemon=True)
    camera_thread.start()
    try:
        while True:
            print(
                f"eye_openness={shared_data['eye_openness']:.3f} "
                f"t_x={shared_data['t_x']:.3f} "
                f"t_y={shared_data['t_y']:.3f} "
                f"pitch_signal={shared_data['pitch_signal']:.3f}"
            )
            if shared_data["blink_detected"]:
                print("BLINK DETECTED")
                shared_data["blink_detected"] = False
            time.sleep(0.1)
    except KeyboardInterrupt:
        shared_data["running"] = False
        camera_thread.join()