import tkinter as tk


class CursorWindow:
    """
    Continuously polls shared_data (gaze/pitch/blink) every POLL_MS via
    root.after() — same non-blocking pattern calibration_window.py used
    for check_capture_done, but here it never stops polling since this
    is a live running loop for as long as the program is open, not a
    one-shot capture sequence.
    """

    POLL_MS = 50  # matches calibration_window.py's polling interval

    def __init__(self, shared_data, zone_classifier, state_machine, pitch_baseline):
        self.shared_data = shared_data
        self.zc = zone_classifier
        self.sm = state_machine
        self.pitch_baseline = pitch_baseline
        self.last_gazed_zone = 0  # which of the 2 boxes gaze currently classifies into

        self.root = tk.Tk()
        self.root.title("EyeControl - Cursor Control")

        self.root.attributes("-fullscreen", True)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        self.canvas = tk.Canvas(self.root, bg="black", width=screen_width, height=screen_height * 0.8)
        self.canvas.pack(fill="both", expand=True)

        self.status_label = tk.Label(
            self.root, text="", font=("Courier", 18), anchor="w", justify="left"
        )
        self.status_label.pack(fill="x", padx=10, pady=5)

        self.root.bind("<Escape>", lambda event: self._quit())

        # Box layout: 2 equal-width boxes spanning the FULL real screen
        # width, matching the 2-zone left/right geometry the classifier
        # was trained on (see zone_classifier.py's get_zone).
        self.screen_width = screen_width
        self.box_width = screen_width / 2
        self.box_height = screen_height * 0.75

    def _quit(self):
        self.shared_data["running"] = False
        self.root.destroy()

    def poll(self):
        gaze_x = self.shared_data["t_x"]
        pitch = self.shared_data["pitch_signal"]
        delta = pitch - self.pitch_baseline
        mode = self.sm.update_pitch(pitch)

        if mode == "SELECT":
            zone = self.zc.predict_zone(gaze_x)
            self.last_gazed_zone = zone[0]

            if self.shared_data["blink_detected"]:
                self.shared_data["blink_detected"] = False
                result = self.sm.confirm_zone(self.last_gazed_zone)
        else:
            print(f"MODE={mode} pitch={pitch:.3f} delta={delta:+.3f}")
            self.shared_data["blink_detected"] = False

        self._draw()
        self.root.after(self.POLL_MS, self.poll)

    def _draw(self):
        self.canvas.delete("all")
        options = self.sm.current_options()

        for zone_index in range(2):
            x0 = zone_index * self.box_width
            x1 = x0 + self.box_width
            label = options.get(zone_index, "")

            is_gazed = (self.sm.mode == "SELECT" and zone_index == self.last_gazed_zone)
            fill = "#3a3a3a" if is_gazed else "#111111"

            self.canvas.create_rectangle(
                x0 + 5, 5, x1 - 5, self.box_height,
                fill=fill, outline="#666666", width=2
            )
            self.canvas.create_text(
                (x0 + x1) / 2, self.box_height / 2,
                text=label, fill="white", font=("Courier", 28)
            )

        status = (
            f"MODE: {self.sm.mode}"
            f"{'  (' + self.sm.scroll_direction + ')' if self.sm.mode == 'SCROLL' else ''}"
            f"   DEPTH: {len(self.sm.path)}"
            f"   INPUT: {self.sm.typed_input}"
        )
        self.status_label.config(text=status)

    def run(self):
        self.poll()  # kicks off the recurring poll loop before mainloop blocks
        self.root.mainloop()