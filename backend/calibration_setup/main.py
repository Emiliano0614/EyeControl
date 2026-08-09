import threading
import time
from backend.calibration_setup.camera_thread import run_camera
from backend.calibration_setup.calibration_window import CalibrationWindow
shared_data = {
    "t_x": 0,
    "t_y": 0,
    "pitch_signal": 0,
    "capturing": False,
    "running": True
}
camera_thread = threading.Thread(target=run_camera, args=(shared_data,), daemon=True)
camera_thread.start()
cal = CalibrationWindow(shared_data)
cal.draw_target()
cal.run()