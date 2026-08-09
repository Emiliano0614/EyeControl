import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import statistics
from backend.engine.gaze_math import gaze_math

# Local copy inside the repo (not a path back into cv-practice) so anyone
# who clones this repo has the model file too — see design discussion.
model_path = 'backend/model/face_landmarker.task'

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)
landmarker = vision.FaceLandmarker.create_from_options(options)

# Burst-capture buffers only — this file is calibration-only and runs
# once, so there's no need for the always-on sliding window that the
# LIVE camera_thread.py (engine/) uses. That one needs continuous
# smoothed values for something on screen in real time; this one only
# ever needs one clean median per target point, computed on demand.
capture_buffer_x = []
capture_buffer_y = []
capture_buffer_pitch_signal = []

def run_camera(shared_data):
    cap = cv2.VideoCapture(0)
    frame_timestamp_ms = 0
    while shared_data["running"] == True:
        ret, frame = cap.read()
        # A failed read returns frame=None — passing that into cv2.cvtColor
        # crashes the loop outright, not just produces bad data. Skipping
        # the frame and trying again next iteration is the fix.
        if not ret:
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        frame_timestamp_ms += 33  # fake increasing timestamp, not real elapsed time

        result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)
        if result.face_landmarks:
            nose_tip = result.face_landmarks[0][1]
            left_iris_center = result.face_landmarks[0][468]
            left_eye_outer_corner = result.face_landmarks[0][33]
            left_eye_inner_corner = result.face_landmarks[0][133]
            left_upper_eyelid = result.face_landmarks[0][159]
            left_lower_eyelid = result.face_landmarks[0][145]

            gaze = gaze_math(left_eye_inner_corner, left_eye_outer_corner, nose_tip,
                              left_upper_eyelid, left_lower_eyelid, left_iris_center)

            # calibration_window.py flips "capturing" True on a spacebar press.
            # Buffer 15 raw samples (not just use one frame) so the saved
            # calibration point is resistant to a stray blink/glance — a
            # median of 15 rides out a single bad frame; one raw frame doesn't.
            if shared_data["capturing"] == True:
                capture_buffer_x.append(gaze["t_x"])
                capture_buffer_y.append(gaze["t_y"])
                capture_buffer_pitch_signal.append(gaze["pitch_signal"])

                if (len(capture_buffer_x) == 15 and len(capture_buffer_y) == 15
                        and len(capture_buffer_pitch_signal) == 15):
                    shared_data["t_x"] = statistics.median(capture_buffer_x)
                    shared_data["t_y"] = statistics.median(capture_buffer_y)
                    shared_data["pitch_signal"] = statistics.median(capture_buffer_pitch_signal)
                    shared_data["capturing"] = False  # signals calibration_window.py this point is done

                    capture_buffer_x.clear()
                    capture_buffer_y.clear()
                    capture_buffer_pitch_signal.clear()