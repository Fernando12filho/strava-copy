from datetime import timedelta
from math import exp

CTL_DAYS = 42
ATL_DAYS = 7


def _interpolate(times, distances, target_distance):
    for i in range(1, len(distances)):
        if distances[i] >= target_distance:
            d0, d1 = distances[i - 1], distances[i]
            t0, t1 = times[i - 1], times[i]
            if d1 == d0:
                return t1
            fraction = (target_distance - d0) / (d1 - d0)
            return t0 + fraction * (t1 - t0)
    return None


def best_effort(times, distances, target_distance_meters):
    if distances[-1] - distances[0] < target_distance_meters:
        return None

    best = None
    for i in range(len(distances)):
        target = distances[i] + target_distance_meters
        crossing_time = _interpolate(times[i:], distances[i:], target)
        if crossing_time is None:
            break
        duration = crossing_time - times[i]
        if best is None or duration < best:
            best = duration
    return best


def is_new_best_effort(existing_seconds, candidate_seconds):
    if existing_seconds is None:
        return True
    return candidate_seconds < existing_seconds


def _zone_for_hr(hr, zones):
    matched = None
    for zone in sorted(zones, key=lambda z: z["min_bpm"]):
        if hr >= zone["min_bpm"]:
            matched = zone
        else:
            break
    return matched["zone_number"] if matched else None


def time_in_zone(times, hr_values, zones):
    zone_seconds = {zone["zone_number"]: 0.0 for zone in zones}
    for i in range(len(times) - 1):
        dt = times[i + 1] - times[i]
        zone_number = _zone_for_hr(hr_values[i], zones)
        if zone_number is not None:
            zone_seconds[zone_number] += dt
    return zone_seconds


def km_splits(times, distances, split_meters=1000.0):
    total_distance = distances[-1]
    splits = []
    prev_time = times[0]
    covered = 0.0
    boundary = split_meters
    while boundary <= total_distance:
        crossing_time = _interpolate(times, distances, boundary)
        splits.append(
            {
                "distance_meters": split_meters,
                "duration_seconds": crossing_time - prev_time,
                "pace_per_km_seconds": (crossing_time - prev_time) / (split_meters / 1000.0),
            }
        )
        prev_time = crossing_time
        covered = boundary
        boundary += split_meters

    remainder = total_distance - covered
    if remainder > 0:
        end_time = times[-1]
        splits.append(
            {
                "distance_meters": remainder,
                "duration_seconds": end_time - prev_time,
                "pace_per_km_seconds": (end_time - prev_time) / (remainder / 1000.0),
            }
        )
    return splits


# Empirical grade-adjustment constant: running pace slows ~3.3% per 1% incline.
GRADE_ADJUSTMENT_FACTOR = 0.033


def grade_adjusted_pace(raw_pace_sec_per_km, grade_percent):
    return raw_pace_sec_per_km * (1 + GRADE_ADJUSTMENT_FACTOR * grade_percent)


def trimp(duration_minutes, avg_hr, hr_rest, hr_max, gender="male"):
    delta_ratio = (avg_hr - hr_rest) / (hr_max - hr_rest)
    if gender == "male":
        weighting = 0.64 * exp(1.92 * delta_ratio)
    else:
        weighting = 0.86 * exp(1.67 * delta_ratio)
    return duration_minutes * delta_ratio * weighting


def ctl_atl(daily_loads):
    ctl_decay = 1 - exp(-1 / CTL_DAYS)
    atl_decay = 1 - exp(-1 / ATL_DAYS)

    results = []
    ctl = atl = None
    for load in daily_loads:
        ctl = load if ctl is None else ctl + (load - ctl) * ctl_decay
        atl = load if atl is None else atl + (load - atl) * atl_decay
        results.append({"ctl": ctl, "atl": atl, "form": ctl - atl})
    return results


def riegel_predict(known_time_seconds, known_distance_meters, target_distance_meters, exponent=1.06):
    return known_time_seconds * (target_distance_meters / known_distance_meters) ** exponent


def estimate_vo2max(distance_meters, duration_seconds, avg_hr=None, max_hr=None):
    velocity = distance_meters / (duration_seconds / 60)
    vo2_at_pace = -4.60 + 0.182258 * velocity + 0.000104 * velocity**2
    t_minutes = duration_seconds / 60
    percent_max = (
        0.8
        + 0.1894393 * exp(-0.012778 * t_minutes)
        + 0.2989558 * exp(-0.1932605 * t_minutes)
    )
    vdot = vo2_at_pace / percent_max
    if avg_hr and max_hr:
        vdot *= max_hr / avg_hr
    return vdot


def coalesce_stream_metric(times, values):
    pairs = [(t, v) for t, v in zip(times, values) if v is not None]
    if not pairs:
        return [], []
    ts, vs = zip(*pairs)
    return list(ts), list(vs)


def build_daily_trimp_loads(daily_totals, start_date, end_date):
    loads = []
    current = start_date
    while current <= end_date:
        loads.append(daily_totals.get(current, 0.0))
        current += timedelta(days=1)
    return loads


def default_max_hr(birth_year, reference_year):
    return 220 - (reference_year - birth_year)


def value_at_time(times, values, target_time):
    if not times:
        return None
    closest_index = min(range(len(times)), key=lambda i: abs(times[i] - target_time))
    return values[closest_index]
