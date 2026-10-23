"""
Tekrar sayaci.

Sayim, referans kare eslesmesine degil hareket dongusune gore yapilir.
cv2 ve mediapipe kullanmaz; sentetik aci serileriyle test edilebilir.
"""

import os
import time

AMPLITUDE_MIN_RATIO = 0.70
RANGE_MIN_DEGREES = 15.0
MOVE_ENTER = 0.20
RETURN_BELOW = 0.25
MIN_REP_SECONDS = 0.6
MAX_REP_SECONDS = 15.0
VISIBILITY_HOLD_SECONDS = 0.5
PROGRESS_CAP = 1.3
STABLE_TOLERANCE_DEG = 25.0
FORM_CHECK_ENABLED = True
STABLE_FAIL_RATIO = 0.25
FORM_HINT_SECONDS = 0.5
STABLE_PRESENCE_MIN = 0.80

JOINT_NAMES_TR = {
    'sol_dirsek': 'Sol Dirsek', 'sag_dirsek': 'Sag Dirsek',
    'sol_omuz': 'Sol Omuz', 'sag_omuz': 'Sag Omuz',
    'sol_kalca': 'Sol Kalca', 'sag_kalca': 'Sag Kalca',
    'sol_diz': 'Sol Diz', 'sag_diz': 'Sag Diz',
}

DEBUG_REP = os.getenv('DEBUG_REP', '0').strip().lower() in ('1', 'true', 'yes')


def _mean(values):
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _percentile(values, q):
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * (q / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return float(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)


def _extrema(values):
    maxima = []
    minima = []
    for i in range(1, len(values) - 1):
        cur = values[i]
        prev = values[i - 1]
        nxt = values[i + 1]
        if cur >= prev and cur >= nxt and (cur > prev or cur > nxt):
            maxima.append(float(cur))
        if cur <= prev and cur <= nxt and (cur < prev or cur < nxt):
            minima.append(float(cur))
    return maxima, minima


def joint_profile_from_track(name, values):
    """Doktor videosundaki bir eklem icin start/peak cikar."""
    if not values or len(values) < 6:
        return None
    series = [float(v) for v in values]
    p10 = _percentile(series, 10)
    p90 = _percentile(series, 90)
    if (p90 - p10) <= RANGE_MIN_DEGREES:
        return None

    maxima, minima = _extrema(series)
    if not maxima:
        maxima = [p90]
    if not minima:
        minima = [p10]
    high = _mean(maxima)
    low = _mean(minima)
    if abs(high - low) <= RANGE_MIN_DEGREES:
        high, low = p90, p10
        if abs(high - low) <= RANGE_MIN_DEGREES:
            return None

    head = series[:3]
    origin = _mean(head)
    if abs(origin - high) <= abs(origin - low):
        start, peak = high, low
    else:
        start, peak = low, high
    return {'name': name, 'start': float(start), 'peak': float(peak)}


def build_profiles(tracks):
    leads, _stable = build_joint_model(tracks)
    return leads


def _median(values):
    return _percentile(values, 50)


def build_joint_model(tracks, total_frames=None):
    """Sol/sag eklemler ayri ayri: hareketli olanlar lead, sabit olanlar destek."""
    leads = []
    stable = []
    lengths = [len(v) for v in (tracks or {}).values() if v]
    frame_count = int(total_frames or (max(lengths) if lengths else 0))
    for name, values in (tracks or {}).items():
        series = [float(v) for v in values if v is not None]
        if len(series) < 6:
            continue
        span = _percentile(series, 90) - _percentile(series, 10)
        median = _median(series)
        presence = (len(series) / frame_count) if frame_count else 1.0
        if span >= RANGE_MIN_DEGREES:
            profile = joint_profile_from_track(name, series)
            if profile:
                profile['median'] = float(median)
                profile['span'] = float(span)
                profile['role'] = 'lead'
                leads.append(profile)
        elif span < RANGE_MIN_DEGREES and presence >= STABLE_PRESENCE_MIN:
            stable.append({
                'name': name,
                'median': float(median),
                'span': float(span),
                'role': 'stable',
            })
    leads.sort(key=lambda item: abs(item['peak'] - item['start']), reverse=True)
    return leads, stable


def _joint_progress(angle, start, peak):
    span = peak - start
    if abs(span) < 1e-6:
        return 0.0
    raw = (float(angle) - start) / span
    if raw < 0.0:
        return 0.0
    if raw > PROGRESS_CAP:
        return PROGRESS_CAP
    return raw


class RepCounter:
    """IDLE -> MOVING -> AT_PEAK -> RETURNING -> sayilan tekrar."""

    def __init__(self):
        self.profiles = []
        self.stable = []
        self.state = 'IDLE'
        self.count = 0
        self.attempts = 0
        self._cycle_start = None
        self._peak_progress = 0.0
        self._qualities = []
        self._gap_since = None
        self._last_progress = 0.0
        self._stable_bad = {}
        self._stable_seen = {}
        self._stable_bad_since = {}
        self.qualities = []
        self.last_hints = []

    def configure(self, profiles, stable=None):
        self.profiles = [dict(item) for item in (profiles or [])]
        self.stable = [dict(item) for item in (stable or [])]
        self.reset()

    def export_profiles(self):
        return [dict(item) for item in self.profiles]

    def export_stable(self):
        return [dict(item) for item in self.stable]

    @property
    def configured(self):
        return bool(self.profiles)

    def reset(self):
        self.state = 'IDLE'
        self.count = 0
        self.attempts = 0
        self._cycle_start = None
        self._peak_progress = 0.0
        self._qualities = []
        self._gap_since = None
        self._last_progress = 0.0
        self._reset_stable_counts()
        self.qualities = []
        self.last_hints = []

    def mean_quality(self):
        return _mean(self.qualities) if self.qualities else 0.0

    def progress_of(self, angles):
        parts = []
        missing = False
        for profile in self.profiles:
            name = profile['name']
            if name not in angles or angles[name] is None:
                missing = True
                continue
            parts.append(_joint_progress(angles[name], profile['start'], profile['peak']))
        if not parts:
            return None, True
        return _mean(parts), missing

    def update(self, angles, now=None, quality=None, visibility=None):
        if now is None:
            now = time.monotonic()
        if not self.configured:
            return self._decision(0.0, 0.0, 0.0, quality or 0.0, False, 'no_profile')

        if self._lead_missing(angles, visibility):
            return self._hold_for_gap(now, quality)

        self._gap_since = None
        progress, _missing = self.progress_of(angles)
        if progress is None:
            return self._hold_for_gap(now, quality)
        self._last_progress = progress

        if self.state != 'IDLE':
            self._peak_progress = max(self._peak_progress, progress)
            if quality is not None:
                self._qualities.append(float(quality))
            self.last_hints = self._observe_stable(angles, now)
            elapsed = now - (self._cycle_start or now)
            if elapsed > MAX_REP_SECONDS:
                return self._abort(progress, elapsed, 'too_long')

        if self.state == 'IDLE':
            if progress > MOVE_ENTER:
                self._begin_cycle(now, progress, quality)
                self.last_hints = self._observe_stable(angles, now)
            return self._decision(progress, self._peak_progress, 0.0, quality or 0.0, False, None)

        if self.state == 'MOVING' and progress >= AMPLITUDE_MIN_RATIO:
            self.state = 'AT_PEAK'

        if self.state == 'AT_PEAK' and progress < AMPLITUDE_MIN_RATIO:
            self.state = 'RETURNING'

        if progress < RETURN_BELOW:
            elapsed = now - (self._cycle_start or now)
            if self._peak_progress < AMPLITUDE_MIN_RATIO:
                return self._abort(progress, elapsed, 'amplitude')
            if elapsed < MIN_REP_SECONDS:
                return self._abort(progress, elapsed, 'too_short')
            form_joint = self._form_violation()
            if form_joint:
                return self._abort(progress, elapsed, 'form', form_joint, failed_attempt=True)
            return self._complete(progress, elapsed)

        return self._decision(
            progress,
            self._peak_progress,
            now - (self._cycle_start or now),
            self._cycle_quality(quality),
            False,
            None,
        )

    def _lead_missing(self, angles, visibility):
        for profile in self.profiles:
            name = profile['name']
            if visibility is not None and name in visibility and visibility[name] < 0.5:
                return True
            if name not in angles or angles.get(name) is None:
                return True
        return False

    def _hold_for_gap(self, now, quality):
        if self.state == 'IDLE':
            return self._decision(self._last_progress, 0.0, 0.0, quality or 0.0, False, None)
        if self._gap_since is None:
            self._gap_since = now
        if (now - self._gap_since) < VISIBILITY_HOLD_SECONDS:
            return self._decision(
                self._last_progress,
                self._peak_progress,
                now - (self._cycle_start or now),
                self._cycle_quality(quality),
                False,
                'hold',
            )
        return self._abort(self._last_progress, now - (self._cycle_start or now), 'visibility')

    def _reset_stable_counts(self):
        names = [item['name'] for item in self.stable]
        self._stable_bad = {name: 0 for name in names}
        self._stable_seen = {name: 0 for name in names}
        self._stable_bad_since = {name: None for name in names}

    def _observe_stable(self, angles, now):
        hints = []
        if not FORM_CHECK_ENABLED:
            return hints
        for joint in self.stable:
            name = joint['name']
            if name not in angles or angles[name] is None:
                continue
            self._stable_seen[name] = self._stable_seen.get(name, 0) + 1
            delta = abs(float(angles[name]) - float(joint['median']))
            if delta > STABLE_TOLERANCE_DEG:
                self._stable_bad[name] = self._stable_bad.get(name, 0) + 1
                started = self._stable_bad_since.get(name)
                if started is None:
                    self._stable_bad_since[name] = now
                elif (now - started) >= FORM_HINT_SECONDS:
                    ref = float(joint['median'])
                    label = JOINT_NAMES_TR.get(name, name)
                    hints.append(f"{label}: pozisyonu koruyun (doktor: {ref:.0f}°)")
            else:
                self._stable_bad_since[name] = None
        return hints

    def _form_violation(self):
        if not FORM_CHECK_ENABLED:
            return None
        for joint in self.stable:
            name = joint['name']
            seen = self._stable_seen.get(name, 0)
            if seen <= 0:
                continue
            if (self._stable_bad.get(name, 0) / seen) > STABLE_FAIL_RATIO:
                return name
        return None

    def _begin_cycle(self, now, progress, quality):
        self.state = 'MOVING'
        self._cycle_start = now
        self._peak_progress = progress
        self._qualities = []
        self._reset_stable_counts()
        if quality is not None:
            self._qualities.append(float(quality))
        if progress >= AMPLITUDE_MIN_RATIO:
            self.state = 'AT_PEAK'

    def _cycle_quality(self, fallback):
        if self._qualities:
            return _mean(self._qualities)
        return float(fallback or 0.0)

    def _complete(self, progress, elapsed):
        peak = self._peak_progress
        quality = self._cycle_quality(0.0)
        self.count += 1
        self.qualities.append(quality)
        self.state = 'IDLE'
        self._cycle_start = None
        self._peak_progress = 0.0
        self._qualities = []
        self._reset_stable_counts()
        return self._decision(progress, peak, elapsed, quality, True, None)

    def _abort(self, progress, elapsed, reason, joint=None, failed_attempt=False):
        peak = self._peak_progress
        quality = self._cycle_quality(0.0)
        if failed_attempt:
            self.attempts += 1
        self.state = 'IDLE'
        self._cycle_start = None
        self._peak_progress = 0.0
        self._qualities = []
        self._gap_since = None
        self._reset_stable_counts()
        return self._decision(progress, peak, elapsed, quality, False, reason, joint)

    def _decision(self, progress, peak, duration, quality, counted, reason, joint=None):
        shown_peak = peak
        if DEBUG_REP and (counted or reason in ('amplitude', 'too_short', 'too_long', 'visibility', 'form')):
            outcome = 'counted' if counted else 'rejected'
            print(
                f"[REP] progress={progress:.2f} peak={shown_peak:.2f} "
                f"duration={duration:.2f}s quality={quality:.2f} "
                f"result={outcome} reason={reason or '-'} joint={joint or '-'}"
            )
        return {
            'counted': counted,
            'progress': round(float(progress), 4),
            'peak': round(float(shown_peak), 4),
            'duration': round(float(duration), 4),
            'quality': round(float(quality), 4),
            'reason': reason,
            'joint': joint,
            'hints': list(self.last_hints),
            'state': self.state,
            'count': self.count,
            'attempts': self.attempts,
        }
