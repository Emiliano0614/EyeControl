import tkinter as tk
import json

class CalibrationWindow:
    def __init__(self, shared_data):
        self.shared_data = shared_data
        self.current_target_index = 0
        self.results = []
        self.calibration_step = 0

        self.root = tk.Tk()
        # Must go fullscreen BEFORE reading winfo_screenwidth/height — asking
        # before fullscreen returns the smaller default window size, not the
        # real display, which would put every target in the wrong spot.
        self.root.attributes("-fullscreen", True)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 5 rows x 3 cols = 15 points. Started as 3x3 (9 points), but vertical
        # was the consistently weak signal axis — 3 rows wasn't enough
        # resolution to see how it behaved between top/center/bottom. The two
        # extra rows (1/4 and 3/4 height) were added specifically to get more
        # vertical data, testing whether row separation would tighten up.
        center_x, center_y = screen_width / 2, screen_height / 2
        upper_mid_y = screen_height / 4
        lower_mid_y = screen_height * 3 / 4
        top_left_x = 0
        top_left_y = 0
        top_middle_x = screen_width / 2
        top_middle_y = 0
        top_right_x = screen_width
        top_right_y = 0

        upper_left_x = 0
        upper_middle_x = screen_width / 2
        upper_right_x = screen_width

        center_left_x = 0
        center_left_y = screen_height / 2
        center_right_x = screen_width
        center_right_y = screen_height / 2

        lower_left_x = 0
        lower_middle_x = screen_width / 2
        lower_right_x = screen_width

        
        bottom_left_x = 0
        bottom_left_y = screen_height
        bottom_center_x = screen_width / 2
        bottom_center_y = screen_height
        bottom_right_x = screen_width
        bottom_right_y = screen_height

        self.calibration_targets = [
            (center_x, center_y),
            (top_middle_x, top_middle_y),
            (top_left_x, top_left_y),
            (top_right_x, top_right_y),
            (center_left_x, center_left_y),
            (center_right_x, center_right_y),
            (bottom_left_x, bottom_left_y),
            (bottom_center_x, bottom_center_y),
            (bottom_right_x, bottom_right_y),
            (upper_left_x, upper_mid_y),
            (upper_middle_x, upper_mid_y),
            (upper_right_x, upper_mid_y),
            (lower_left_x, lower_mid_y),
            (lower_middle_x, lower_mid_y),
            (lower_right_x, lower_mid_y),
        ]

        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.root.bind("<space>", self.start_capture)
        self.root.bind("<Escape>", lambda event: self.root.destroy())

    def check_capture_done(self):
        # Polls instead of blocking, since mainloop() has to keep running.
        # This is how it "notices" camera_thread.py finished a burst —
        # nothing calls it externally after start_capture, it just
        # re-schedules itself every 50ms until "capturing" flips False.
        if self.shared_data["capturing"] == True:
            self.root.after(50, self.check_capture_done)
        else:
            median_X = self.shared_data["t_x"]
            median_Y = self.shared_data["t_y"]
            median_pitch_signal = self.shared_data["pitch_signal"]
            target_x, target_y = self.calibration_targets[self.current_target_index]
            self.results.append((median_X, median_Y, target_x, target_y, median_pitch_signal))

            self.current_target_index += 1
            if self.current_target_index > 14:  # 15 points, indices 0-14
                with open(f"backend/calibration/calibration_run{self.calibration_step}.json", "w") as f:
                    json.dump(self.results, f)
                self.results = []
                self.current_target_index = 0
                self.calibration_step += 1
                # step starts at 0, saves run0-run3 (4 files) across steps
                # 0,1,2,3 — after the 4th save step becomes 4, so >3 is what
                # correctly stops after exactly 4 full sweeps.
                if self.calibration_step > 3:
                    print("Finished Calibration")
                    self.shared_data["running"] = False  # tells camera_thread.py to stop next iteration
                    self.root.destroy()
                else:
                    self.draw_target()
            else:
                self.draw_target()

    def start_capture(self, event):
        self.shared_data["capturing"] = True  # the one signal camera_thread.py's loop is watching for
        self.check_capture_done()

    def run(self):
        self.root.mainloop()

    def draw_target(self):
        self.x, self.y = self.calibration_targets[self.current_target_index]
        # Radius 55, not a small dot — at true screen edges (y=0 or
        # y=screen_height) a small dot got clipped/invisible, confirmed via
        # testing that macOS's auto-hide Dock reserves edge space even
        # hidden. Coordinates stay at the true edges for accuracy; the
        # circle's just made big enough that some of it always shows.
        self.radius = 55
        self.x0, self.x1 = self.x - self.radius, self.x + self.radius
        self.y0, self.y1 = self.y - self.radius, self.y + self.radius
        self.canvas.delete("all")
        self.canvas.create_oval(self.x0, self.y0, self.x1, self.y1)