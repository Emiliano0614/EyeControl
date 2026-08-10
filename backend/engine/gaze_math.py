def gaze_math(left_eye_inner_corner, left_eye_outer_corner, nose_tip, left_upper_eyelid, left_lower_eyelid, left_iris_center):
    """
    Pure math, no camera/loop here — one frame's landmarks in, gaze/pitch
    numbers out. Lives in engine/ so both camera_thread.py and the
    calibration script can import it instead of duplicating the formula.

    KNOWN LIMITATION ( confirmed via live testing, not
    fixed): at extreme diagonal gaze, eye_corner_distance gets distorted
    since the eye corners no longer present a flat span to the camera.
    Accepted edge case.
    """
    # t = (P - A) / (B - A): Where the iris (P) sits between the outer eye corner (A, t=0) and
    # inner eye corner (B, t=1). t=0.5 is roughly centered.
    x_numerator = left_iris_center.x - left_eye_outer_corner.x
    x_denominator = left_eye_inner_corner.x - left_eye_outer_corner.x
    t_X = x_numerator / x_denominator

    y_numerator = left_iris_center.y - left_upper_eyelid.y
    y_denominator = left_lower_eyelid.y - left_upper_eyelid.y
    t_Y = y_numerator / y_denominator

    # pitch_signal: how far nose tip sits below eye level, normalized by
    # eye corner distance so it isn't affected by camera distance
    eye_level_y = (left_eye_outer_corner.y + left_eye_inner_corner.y) / 2
    eye_corner_distance = abs(left_eye_outer_corner.x - left_eye_inner_corner.x)
    pitch_signal = (nose_tip.y - eye_level_y) / eye_corner_distance

    return {
        "t_x": t_X,
        "t_y": t_Y,
        "pitch_signal": pitch_signal
    }
def eye_openness_math(left_upper_eyelid, left_lower_eyelid, left_eye_outer_corner, left_eye_inner_corner):
    """
    Pure math, one frame's landmarks in, a single ratio out. Same shape
    as gaze_math() above — no camera/loop state, reused by both
    camera_thread.py (blink detection) and any calibration/tuning script
    that wants to inspect eye_openness directly.
    """
    eye_corner_distance = abs(left_eye_outer_corner.x - left_eye_inner_corner.x)
    eye_gap = abs(left_upper_eyelid.y - left_lower_eyelid.y)
    return eye_gap / eye_corner_distance