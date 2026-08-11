from .Drill_tree import TREE
class CursorStateMachine:
    def __init__(self, pitch_baseline, scroll_delta=0.15):
        self.pitch_baseline = pitch_baseline
        self.scroll_delta = scroll_delta
        self.mode = "SELECT"
        self.path = []
        self.typed_input = ""
        self.scroll_direction = None
    def update_pitch(self, pitch_signal):
        delta = pitch_signal - self.pitch_baseline
        was_select = (self.mode == "SELECT")
        if abs(delta) > self.scroll_delta:
            self.mode = "SCROLL"
            self.scroll_direction = "DOWN" if delta > 0 else "UP"
            if was_select:
                self._reset_drill()
        else:
            self.mode = "SELECT"
            self.scroll_direction = None
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
    sm = CursorStateMachine(pitch_baseline=1.0, scroll_delta=0.15)

    print("--- Test 1: neutral pitch, stay in SELECT ---")
    print(sm.update_pitch(1.05))  # small wobble, still under 0.15 delta
    print("mode:", sm.mode, "direction:", sm.scroll_direction)

    print("\n--- Test 2: tilt down past threshold, enter SCROLL ---")
    print(sm.update_pitch(1.30))  # delta = 0.30, past scroll_delta
    print("mode:", sm.mode, "direction:", sm.scroll_direction)

    print("\n--- Test 3: tilt up past threshold, enter SCROLL ---")
    print(sm.update_pitch(0.70))  # delta = -0.30
    print("mode:", sm.mode, "direction:", sm.scroll_direction)

    print("\n--- Test 4: back to neutral, SELECT again ---")
    print(sm.update_pitch(1.0))
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
    sm.update_pitch(1.30)  # force SCROLL mode
    print(sm.confirm_zone(0))  # should say ignored_not_in_select_mode

    print("\n--- Test 7: BACKSPACE removes last typed char ---")
    sm.update_pitch(1.0)  # back to SELECT
    # drill to BACKSPACE: right branch (1) -> right (1) -> left (0) -> right (1)
    print(sm.confirm_zone(1))
    print(sm.confirm_zone(1))
    print(sm.confirm_zone(0))
    print(sm.confirm_zone(1))
    print("typed_input after backspace:", sm.typed_input)