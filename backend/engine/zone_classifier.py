import json
import os
import statistics

# Only 2 zones (LEFT/RIGHT) — no vertical split. Matches cv-practice
# 05's final proven design, reused deliberately rather than re-derived,
# per explicit instruction: cv-practice's separability testing is
# trusted, not repeated here on EyeControl's own calibration data.
ZONE_COUNT = 2


def get_zone(x, y):
    """
    Buckets a calibration TARGET position into LEFT (0) or RIGHT (1).

    Calibration grid has 3 real x-columns: x=0 (left edge), x=735
    (dead center), x=1470 (right edge).

    MERGE REUSED FROM CV-PRACTICE 05, NOT RE-TESTED HERE: 05 found
    (via leave-one-run-out cross-validation + distance-distribution
    analysis on real calibration data) that old zone A (left) and old
    zone B (center) were NOT separable — their gaze_x distance ranges
    overlapped almost entirely (genuine-A range 0.07-2.15 vs genuine-B
    0.57-4.89). Old zone C (right) WAS reliably separable from B. So
    A+B merged into one LEFT zone, C stayed its own RIGHT zone. This
    same merge (x=0 and x=735 -> LEFT, x=1470 -> RIGHT) is applied
    here as a trusted assumption, since cv-practice's separability
    testing is proven and not being reinvented. If live testing later
    shows LEFT is unreliable on this setup, this is the first place
    to revisit.
    """
    if x == 0 or x == 735:
        zone_x = 0
    else:
        zone_x = 1

    # Returned as a 2-part tuple (zone_x, zone_y) rather than just
    # zone_x, even though zone_y is always 0 right now — matches 05's
    # shape, future-proofs the interface if vertical zones are ever
    # added later without needing to change every call site.
    return (zone_x, 0)


class ZoneClassifier:
    """
    Nearest-centroid classifier, gaze_x ONLY — no gaze_y, no
    pitch_signal in the distance calculation.

    REUSED FROM CV-PRACTICE 05'S FINAL DESIGN (not its first attempt).
    05 originally included pitch_signal and gaze_y in the distance
    calc, and both were removed after live testing showed they
    actively hurt accuracy:
      - pitch_signal contributed nearly equal weight to gaze_x in the
        distance calc, causing zone flips from head tilt ALONE, even
        with gaze_x steady — LEFT/RIGHT is a horizontal-only decision,
        pitch has no business voting on it.
      - gaze_y caused cases where gaze_x alone clearly favored one
        zone (e.g. distance 0.15 vs 1.61), but gaze_y's distance
        dragged the total into a near-tie (1.623 vs 1.629), letting
        gaze_y noise flip the result.
    Root cause in both cases: nearest-centroid distance is additive —
    every included feature votes on the answer regardless of whether
    it's actually relevant to the decision. Since this is a purely
    horizontal decision, only gaze_x is diagnostic; including
    irrelevant or noisy features dilutes or outvotes it. Starting
    directly from gaze_x-only here rather than re-testing 3-feature
    vs 1-feature on EyeControl's own data, since 05 already proved it.
    """

    def __init__(self, calibration_dir="../calibration", num_runs=4):
        self.zone_centroids = {}
        zone_readings = {}
        # Flat, non-zone-split list of every gaze_x reading across all
        # zones — needed to compute the overall spread (stdev) of
        # gaze_x, used later in predict_zone() to normalize raw
        # distances into "how many standard deviations away" instead
        # of a meaningless raw number (0.05 might be huge or tiny
        # depending on how naturally spread out gaze_x is).
        all_gx = []

        for i in range(num_runs):
            path = os.path.join(calibration_dir, f"calibration_run{i}.json")
            with open(path) as f:
                run_data = json.load(f)

            for row in run_data:
                gaze_x, gaze_y, target_x, target_y, pitch_signal = row
                zone = get_zone(target_x, target_y)
                # setdefault(zone, []) returns the existing list for
                # this zone if one exists, or creates+returns a fresh
                # empty list if this is the first reading seen for it
                # — avoids a KeyError on the first hit per zone.
                zone_readings.setdefault(zone, []).append(gaze_x)
                all_gx.append(gaze_x)

        # Average each zone's collected gaze_x readings into a single
        # representative centroid — this IS the entire "model," no
        # regression/coefficients involved (same reasoning as
        # cv-practice's root-caused pivot away from lstsq regression:
        # raw gaze measurement noise nearly matches the real signal
        # range, making regression fundamentally unstable; nearest-
        # centroid avoids that entirely).
        for zone, readings in zone_readings.items():
            self.zone_centroids[zone] = sum(readings) / len(readings)

        # Sanity check: fail loudly, immediately, if something upstream
        # (a missing/corrupt calibration file, a get_zone bug) produced
        # the wrong number of zones — rather than silently misbehaving
        # later during live use with no clear cause.
        if len(self.zone_centroids) != ZONE_COUNT:
            raise ValueError(
                f"Expected {ZONE_COUNT} zone centroids, got "
                f"{len(self.zone_centroids)}. Check calibration_dir and "
                f"that all {num_runs} calibration_run*.json files are present."
            )

        self.std_gx = statistics.stdev(all_gx)

    def predict_zone(self, gaze_x):
        """
        Classify a LIVE gaze_x reading by nearest centroid (squared,
        stdev-normalized distance). Runs every frame — camera_thread.py
        feeds this the current smoothed t_x value.

        Deliberately lean signature (gaze_x only) — no unused gaze_y/
        pitch/pitch_baseline params carried over from 05's old call
        site, since the caller here is being written fresh, not reused
        from cv-practice.
        """
        best_zone = None
        best_dist = float("inf")

        for zone, centroid_gx in self.zone_centroids.items():
            # Normalize by std_gx so distance is measured in "how many
            # standard deviations away," not a raw difference that's
            # meaningless without knowing gaze_x's natural spread.
            dist = ((gaze_x - centroid_gx) / self.std_gx) ** 2
            if dist < best_dist:
                best_dist = dist
                best_zone = zone

        return best_zone