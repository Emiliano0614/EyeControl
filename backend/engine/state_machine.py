from .Drill_tree import TREE
class CursorStateMachine:
    # CHANGED: constructor signature grew significantly from the
    # original single scroll_delta param. Broken down below by what
    # each addition solves.
    def __init__(self, pitch_baseline, scroll_delta_down=0.25, scroll_delta_up=0.15,
                scroll_exit_delta=None, enter_frames_required=3, exit_frames_required=3):
        self.pitch_baseline = pitch_baseline

        # CHANGED: was one shared scroll_delta for both directions.
        # Split into down/up because neck tilt range isn't symmetric —
        # tilting down is more comfortable/natural than tilting up, so
        # forcing both directions to the same threshold meant either
        # down was too twitchy or up required straining the neck to
        # the point of losing sight of the screen.
        self.scroll_delta_down = scroll_delta_down
        self.scroll_delta_up = scroll_delta_up

        # ADDED: exit thresholds, lower than entry thresholds (hysteresis).
        # Without this, mode flipped SCROLL->SELECT->SCROLL rapidly
        # whenever pitch hovered near the single boundary value, since
        # the same exact threshold was used to both enter AND exit —
        # any single noisy frame dipping under it kicked you straight
        # back to SELECT. Exit thresholds scale off each direction's
        # own entry threshold (0.85 ratio), so once scrolling, you have
        # to genuinely release the tilt (not just wobble near the line)
        # to fall back out.
        self.scroll_exit_delta_down = scroll_delta_down * 0.85
        self.scroll_exit_delta_up = scroll_delta_up * 0.85

        # ADDED: frame-debounce counters, same pattern as camera_thread.py's
        # BLINK_FRAMES_REQUIRED/REOPEN_FRAMES_REQUIRED gate. Even with
        # hysteresis alone, a single noisy frame crossing the exit
        # threshold could still flip mode instantly. Requiring N
        # consecutive frames past a threshold before committing to a
        # mode change (in either direction) smooths out that noise —
        # reusing an approach already proven live in this codebase's
        # blink detector, rather than inventing something new.
        self.enter_frames_required = enter_frames_required
        self.exit_frames_required = exit_frames_required
        self._enter_count = 0
        self._exit_count = 0

        self.mode = "SELECT"
        self.path = []
        self.typed_input = ""
        self.scroll_direction = None

    # CHANGED: update_pitch was originally a single if/else on
    # abs(delta) > self.scroll_delta, flipping mode immediately on any
    # single reading. Rewritten as a proper two-state debounced state
    # machine (see comments above for why each piece exists).
    def update_pitch(self, pitch_signal):
        delta = pitch_signal - self.pitch_baseline
        was_select = (self.mode == "SELECT")

        if self.mode == "SCROLL":
            # use the exit threshold matching whichever direction we're
            # currently scrolling in
            exit_threshold = (self.scroll_exit_delta_down if self.scroll_direction == "DOWN"
                            else self.scroll_exit_delta_up)
            if abs(delta) > exit_threshold:
                # still tilted enough to stay in SCROLL — reset the
                # exit debounce counter, and keep direction live in
                # case the person reversed their tilt mid-scroll
                self._exit_count = 0
                self.scroll_direction = "DOWN" if delta > 0 else "UP"
            else:
                self._exit_count += 1
                if self._exit_count >= self.exit_frames_required:
                    self.mode = "SELECT"
                    self.scroll_direction = None
                    self._exit_count = 0
        else:
            # use the entry threshold matching whichever direction the
            # CURRENT delta is pushing toward
            entry_threshold = self.scroll_delta_down if delta > 0 else self.scroll_delta_up
            if abs(delta) > entry_threshold:
                self._enter_count += 1
                if self._enter_count >= self.enter_frames_required:
                    self.mode = "SCROLL"
                    self.scroll_direction = "DOWN" if delta > 0 else "UP"
                    self._enter_count = 0
                    if was_select:
                        self._reset_drill()
            else:
                # BUG FIX: this reset used to live inside the "else" of
                # the INNER if (_enter_count >= enter_frames_required),
                # which meant it fired every single frame that hadn't
                # yet hit the debounce target — resetting the counter
                # back to 0 before it could ever climb past 1. Moved out
                # to be the else of the OUTER threshold check, so it
                # only resets when pitch actually falls back under
                # threshold, not on every non-triggering frame.
                self._enter_count = 0

        return self.mode

    def _reset_drill(self):
        self.path = []
    def _current_node(self):
        node = TREE
        for zone_index in self.path:
            node = node[zone_index]
        return node
    
    def current_options(self):
        node = self._current_node()
        if not isinstance(node, dict):
            return {}
        options = {}
        for zone_index, child in node.items():
            if isinstance(child, str):
                options[zone_index] = child
            else:
                options[zone_index] = self._leaf_preview(child)
        return options
    def _leaf_preview(self, node):
        if isinstance(node, str):
            return node
        leaves = []
        for child in node.values():
            leaves.append(self._leaf_preview(child))
        return "".join(leaves)
    def confirm_zone(self, zone_index):
        if self.mode != "SELECT":
            return {"event": "ignored_not_in_select_mode"}
        node = self._current_node()
        if not isinstance(node, dict) or zone_index not in node:
            return {"event": "ignored_unknown_zone"}
        child = node[zone_index]

        if isinstance(child, dict):
            self.path.append(zone_index)
            return {"event": "drilled_in"}
        
        self._append_key(child)
        self._reset_drill()
        if child == "BACKSPACE":
            return {"event": "backspace"}
        return {"event": "key_typed", "key": child}
    def _append_key(self, key):
        if key == "BACKSPACE":
            self.typed_input = self.typed_input[:-1]
        elif key == "ENTER":
            pass
        else:
            self.typed_input += key
if __name__ == "__main__":
    # Standalone test: no webcam needed. pitch_baseline=1.0 is a fake
    # reference point — we simulate live pitch readings ourselves below.
    #
    # CHANGED: constructor call and several tests below were updated to
    # match the new debounced, direction-split update_pitch(). Tests
    # that used to expect a SINGLE update_pitch() call to instantly flip
    # mode now loop enough times to clear the enter/exit frame debounce
    # — a single call only increments the counter, it doesn't commit.
    sm = CursorStateMachine(pitch_baseline=1.0, scroll_delta_down=0.25, scroll_delta_up=0.15)

    print("--- Test 1: neutral pitch, stay in SELECT ---")
    print(sm.update_pitch(1.05))  # small wobble, still under either threshold
    print("mode:", sm.mode, "direction:", sm.scroll_direction)

    print("\n--- Test 2: tilt down past threshold, enter SCROLL ---")
    # CHANGED: loop 3x to clear enter_frames_required debounce instead
    # of relying on a single call to flip mode.
    for _ in range(3):
        sm.update_pitch(1.30)  # delta=+0.30, past scroll_delta_down (0.25)
    print("mode:", sm.mode, "direction:", sm.scroll_direction)

    print("\n--- Test 3: tilt up past threshold ---")
    # CHANGED: loop 6x — first 3 calls clear exit_frames_required
    # (dropping out of SCROLL/DOWN), but in practice a hard reversal
    # flips scroll_direction immediately while still in SCROLL (see
    # the "still tilted enough" branch above), so this mostly confirms
    # steady state once the reversal settles.
    for _ in range(6):
        sm.update_pitch(0.80)  # delta=-0.20, past scroll_delta_up (0.15)
    print("mode:", sm.mode, "direction:", sm.scroll_direction)


    print("\n--- Test 4: back to neutral, SELECT again ---")
    # CHANGED: loop 3x to clear exit_frames_required debounce — a
    # single call used to be enough when there was no debounce at all.
    for _ in range(3):
        sm.update_pitch(1.0)
    print("mode:", sm.mode, "direction:", sm.scroll_direction)
    print("\n--- Test 5: drill down to a real key ---")
    print("options at root:", sm.current_options())
    print(sm.confirm_zone(0))  # blink LEFT
    print("path after 1 blink:", sm.path)
    print("options now:", sm.current_options())
    print(sm.confirm_zone(0))  # blink LEFT again
    print("path after 2 blinks:", sm.path)
    print("options now:", sm.current_options())
    print(sm.confirm_zone(0))  # blink LEFT again -> should land on "0"
    print("typed_input:", sm.typed_input, "path reset to:", sm.path)

    print("\n--- Test 6: blink while SCROLL should be ignored ---")
    # CHANGED: loop 3x — single call no longer force-enters SCROLL.
    for _ in range(3):
        sm.update_pitch(1.30)  # force SCROLL mode
    print(sm.confirm_zone(0))  # should say ignored_not_in_select_mode

    print("\n--- Test 7: BACKSPACE removes last typed char ---")
    # CHANGED: loop 3x to actually clear the exit debounce back to
    # SELECT before drilling — a single call left mode stuck in SCROLL,
    # which would've made every confirm_zone() below silently no-op.
    for _ in range(3):
        sm.update_pitch(1.0)  # back to SELECT
    # drill to BACKSPACE: right branch (1) -> right (1) -> left (0) -> right (1)
    print(sm.confirm_zone(1))
    print(sm.confirm_zone(1))
    print(sm.confirm_zone(0))
    print(sm.confirm_zone(1))
    print("typed_input after backspace:", sm.typed_input)