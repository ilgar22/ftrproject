"""
Faz hizalayici — fizyoterapist referansina cevrimici dongusel hizalama.

Model:
  1. Referans videodaki eklem aci izleri tekrarlara bolunur (lider eklem ilerlemesi).
  2. Her tekrar N faz ornegine yeniden orneklenir; faz basina eklem ortalamasi (mu)
     ve tekrarlar arasi degiskenlikten ogrenilen tolerans (sigma) cikarilir.
  3. Canli akis, dongusel sablona cevrimici dinamik programlama ile hizalanir:
     her karede faz hucreleri icin (kal / 1 ilerle / 2 ilerle / 3 ilerle) gecisleri,
     unutma katsayili birikimli maliyet ve sablon sonundan basina sarma.
  4. Sarma = bir tekrarin bitisi. Tekrar, dongu boyunca ortalama kalite esigini
     asarsa ve tepe fazina ulasilmissa sayilir; aksi halde basarisiz deneme.
  5. Eklem durumu, hizalanan fazdaki z-skorundan (|a - mu| / sigma) uretilir.

Bu modul cv2 ve mediapipe kullanmaz; sentetik aci serileriyle test edilebilir.
"""

import warnings

import numpy as np

JOINTS = [
    'sol_dirsek', 'sag_dirsek', 'sol_omuz', 'sag_omuz',
    'sol_kalca', 'sag_kalca', 'sol_diz', 'sag_diz',
]
JOINT_INDEX = {name: i for i, name in enumerate(JOINTS)}
JOINT_NAMES_TR = {
    'sol_dirsek': 'Sol Dirsek', 'sag_dirsek': 'Sag Dirsek',
    'sol_omuz': 'Sol Omuz', 'sag_omuz': 'Sag Omuz',
    'sol_kalca': 'Sol Kalca', 'sag_kalca': 'Sag Kalca',
    'sol_diz': 'Sol Diz', 'sag_diz': 'Sag Diz',
}

# Uc noktalar: el (bilek) ve ayak (ayak bilegi) konumlari — kalca merkezli,
# govde boyuna normalize 3B koordinatlar (x, y, z ayri birer oznitelik)
ENDPOINTS = ['sol_el', 'sag_el', 'sol_ayak', 'sag_ayak']
ENDPOINT_NAMES_TR = {
    'sol_el': 'Sol El', 'sag_el': 'Sag El',
    'sol_ayak': 'Sol Ayak', 'sag_ayak': 'Sag Ayak',
}
POS_FEATURES = [f'{e}_{c}' for e in ENDPOINTS for c in 'xyz']
FEATURES = JOINTS + POS_FEATURES
FEATURE_INDEX = {name: i for i, name in enumerate(FEATURES)}

# Sablon
PHASES = 48                 # faz ornegi sayisi
RANGE_MIN_DEGREES = 15.0    # bu degerin altinda hareket eden eklem "sabit" sayilir
SIGMA_FLOOR = 6.0           # derece — poz kestirim gurultusu tabani
SIGMA_NOISE = 5.0           # derece — referansa eklenen olcum gurultusu
SIGMA_SINGLE_REP = 10.0     # referansta tek tekrar varsa kullanilan tolerans
POS_SIGMA_FLOOR = 0.06      # govde birimi — konum toleransi tabani
POS_SIGMA_NOISE = 0.05      # govde birimi — konum olcum gurultusu
POS_SIGMA_SINGLE = 0.12     # govde birimi — tek tekrarli referans
POS_RANGE_MIN = 0.08        # govde birimi — bunun altinda hareket eden konum "sabit"
SMOOTH_WIN = 5              # referans izi yumusatma penceresi (kare)

# Tekrar bolutleme (referans ve ilerleme)
ENTER = 0.25
EXIT = 0.25
PEAK_REACH = 0.70

# Cevrimici hizalama
Z_OK = 1.5
Z_WARN = 2.5
Z_CAP = 4.0
STAY_PENALTY = 0.05
SKIP2_PENALTY = 0.10
SKIP3_PENALTY = 0.35
COST_DECAY = 0.90
QUALITY_SCALE = 4.0         # q = exp(-maliyet / QUALITY_SCALE)
MIN_JOINTS = 3

# Tekrar kabulu
REP_CYCLE_QUALITY = 0.55
PEAK_Z_MAX = 2.0
MIN_REP_SECONDS = 0.6
MAX_REP_SECONDS = 15.0
VISIBILITY_HOLD_SECONDS = 0.6
ATTEMPT_BACKJUMP = 0.10      # faz geri atlamasi (yol degisimi) esigi
ATTEMPT_MIN_PHASE = 0.15     # bu fazi gecmis bir deneme geri atlarsa 'basarisiz' sayilir
ATTEMPT_COOLDOWN = 1.0       # saniye — ardisik deneme raporlari arasi bekleme
SWITCH_MARGIN = 1.5          # yol degistirme icin gereken maliyet farki (histerezis)


# ─── Yardimcilar ─────────────────────────────────────────────────────────────

def _smooth(series, win=SMOOTH_WIN):
    arr = np.asarray(series, dtype=np.float64)
    if arr.size < win or win <= 1:
        return arr
    kernel = np.ones(win) / win
    pad = win // 2
    padded = np.pad(arr, (pad, pad), mode='edge')
    return np.convolve(padded, kernel, mode='valid')[:arr.size]


def frames_to_matrix(frames):
    """[{angles:{...}, points:{...}}, ...] -> (T x F) matris, eksik oznitelik = NaN."""
    T = len(frames)
    mat = np.full((T, len(FEATURES)), np.nan, dtype=np.float64)
    for t, item in enumerate(frames):
        for name, val in (item.get('angles') or {}).items():
            j = FEATURE_INDEX.get(name)
            if j is not None and val is not None:
                mat[t, j] = float(val)
        for name, val in (item.get('points') or {}).items():
            j = FEATURE_INDEX.get(name)
            if j is not None and val is not None:
                mat[t, j] = float(val)
    return mat


def _fill_nan(col):
    """Kisa bosluklari dogrusal doldur; tamamen bos ise None."""
    mask = np.isnan(col)
    if mask.all():
        return None
    if not mask.any():
        return col
    idx = np.arange(col.size)
    out = col.copy()
    out[mask] = np.interp(idx[mask], idx[~mask], col[~mask])
    return out


def joint_roles(mat):
    """Lider (hareketli) ve sabit eklemleri belirle."""
    leads, stable = [], []
    for j, name in enumerate(JOINTS):
        col = mat[:, j]
        valid = col[~np.isnan(col)]
        presence = valid.size / max(mat.shape[0], 1)
        if valid.size < 6:
            continue
        span = float(np.percentile(valid, 90) - np.percentile(valid, 10))
        median = float(np.median(valid))
        if span >= RANGE_MIN_DEGREES:
            sm = _smooth(_fill_nan(col))
            head = float(np.mean(sm[:3]))
            p10, p90 = np.percentile(sm, 10), np.percentile(sm, 90)
            if abs(head - p90) <= abs(head - p10):
                start, peak = float(p90), float(p10)
            else:
                start, peak = float(p10), float(p90)
            leads.append({'name': name, 'start': start, 'peak': peak,
                          'span': span, 'median': median, 'role': 'lead'})
        elif presence >= 0.8:
            stable.append({'name': name, 'median': median, 'span': span, 'role': 'stable'})
    leads.sort(key=lambda d: abs(d['peak'] - d['start']), reverse=True)
    return leads, stable


def progress_signal(mat, leads):
    """Lider eklemlerin ortalama ilerlemesi (0: baslangic, 1: tepe)."""
    if not leads:
        return np.zeros(mat.shape[0])
    parts = []
    for lead in leads:
        col = _fill_nan(mat[:, JOINT_INDEX[lead['name']]])
        if col is None:
            continue
        span = lead['peak'] - lead['start']
        if abs(span) < 1e-6:
            continue
        parts.append(np.clip((_smooth(col) - lead['start']) / span, 0.0, 1.3))
    if not parts:
        return np.zeros(mat.shape[0])
    return np.mean(np.stack(parts, axis=0), axis=0)


def _expand_to_rest(progress, t, direction, max_back=45, rest=0.08):
    """Siniri, ilerlemenin dinlenme duzeyine (<= rest) indigi en yakin kareye tasi."""
    n = len(progress)
    best, steps = t, 0
    i = t
    while 0 <= i < n and steps <= max_back:
        if progress[i] <= rest:
            best = i
            # dinlenme bolgesinin icine girince bir kac kare daha ilerle (orta nokta)
            k, j = 0, i
            while 0 <= j < n and progress[j] <= rest and k < 6:
                best = j
                j += direction
                k += 1
            break
        i += direction
        steps += 1
    return best


def segment_reps(progress):
    """Ilerleme sinyalinden (baslangic, bitis) tekrar araliklari; sinirlar dinlenme duzeyine genisletilir."""
    reps, state, start = [], 'idle', 0
    reached = False
    for t, p in enumerate(progress):
        if state == 'idle':
            if p > ENTER:
                state, start, reached = 'moving', _expand_to_rest(progress, t, -1), False
        else:
            if p >= PEAK_REACH:
                reached = True
            if p < EXIT:
                if reached and (t - start) >= 4:
                    reps.append((start, _expand_to_rest(progress, t, +1)))
                state = 'idle'
    if state != 'idle' and reached and (len(progress) - start) >= 4:
        reps.append((start, len(progress) - 1))
    return reps


def _resample(seg, n=PHASES):
    """(L x J) -> (n x J); NaN sutunlar olduğu gibi NaN kalir."""
    L = seg.shape[0]
    out = np.full((n, seg.shape[1]), np.nan)
    src = np.linspace(0.0, 1.0, L)
    dst = np.linspace(0.0, 1.0, n)
    for j in range(seg.shape[1]):
        col = _fill_nan(seg[:, j])
        if col is None:
            continue
        out[:, j] = np.interp(dst, src, _smooth(col))
    return out


def build_template(frames):
    """Referans karelerinden faz sablonu uret. JSON'a yazilabilir sozluk doner."""
    mat = frames_to_matrix(frames)
    if mat.shape[0] < 8:
        return None
    leads, stable = joint_roles(mat)
    if not leads:
        return None
    prog = progress_signal(mat, leads)
    reps = segment_reps(prog)
    if not reps:
        reps = [(0, mat.shape[0] - 1)]

    stacks = [_resample(mat[a:b + 1]) for a, b in reps]
    cube = np.stack(stacks, axis=0)                     # K x N x F
    with np.errstate(all='ignore'), warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        mu = np.nanmean(cube, axis=0)                   # N x F
        sd = np.nanstd(cube, axis=0) if cube.shape[0] >= 2 else None
    n_ang = len(JOINTS)
    floor_vec = np.array([SIGMA_FLOOR] * n_ang + [POS_SIGMA_FLOOR] * len(POS_FEATURES))
    noise_vec = np.array([SIGMA_NOISE] * n_ang + [POS_SIGMA_NOISE] * len(POS_FEATURES))
    single_vec = np.array([SIGMA_SINGLE_REP] * n_ang + [POS_SIGMA_SINGLE] * len(POS_FEATURES))
    if sd is not None:
        sigma = np.sqrt(sd ** 2 + noise_vec[None, :] ** 2)
    else:
        sigma = np.tile(single_vec, (mu.shape[0], 1))
    sigma = np.maximum(sigma, floor_vec[None, :])
    sigma[np.isnan(mu)] = np.nan

    # oznitelik agirliklari: eklemler hareket genisligine gore, konumlar sabit katsayiyla
    weights = np.zeros(len(FEATURES))
    for d in leads:
        weights[FEATURE_INDEX[d['name']]] = float(np.clip(d['span'] / 40.0, 0.5, 1.0))
    for d in stable:
        weights[FEATURE_INDEX[d['name']]] = 0.4
    for j in range(n_ang, len(FEATURES)):
        col = mat[:, j]
        valid = col[~np.isnan(col)]
        if valid.size < 6:
            continue
        span = float(np.percentile(valid, 90) - np.percentile(valid, 10))
        weights[j] = 0.3 if span < POS_RANGE_MIN else float(np.clip(span / 0.4, 0.3, 0.6))

    # tepe fazi: ortalama ilerleme izinin en yuksek oldugu faz
    prog_cube = np.stack([_resample(prog[a:b + 1][:, None])[:, 0] for a, b in reps], 0)
    peak_phase = int(np.argmax(np.nanmean(prog_cube, axis=0)))

    rep_lengths = [b - a + 1 for a, b in reps]
    return {
        'phases': PHASES,
        'joints': list(JOINTS),
        'features': list(FEATURES),
        'mu': np.where(np.isnan(mu), None, np.round(mu, 2)).tolist(),
        'sigma': np.where(np.isnan(sigma), None, np.round(sigma, 2)).tolist(),
        'weights': [round(float(w), 3) for w in weights],
        'peak_phase': peak_phase,
        'lead_joints': [d['name'] for d in leads],
        'rep_profile': leads,
        'stable_profile': stable,
        'rep_count': len(reps),
        'rep_len_frames': float(np.mean(rep_lengths)),
    }


# ─── Cevrimici hizalayici ────────────────────────────────────────────────────

class OnlineAligner:
    """Dongusel sablona kare kare hizalama; tekrar sayimi hizalama yolundan turer."""

    def __init__(self, template=None):
        self.template = None
        self.count = 0
        self.attempts = 0
        self.qualities = []
        self.last_hints = []
        if template:
            self.configure(template)

    # ─ kurulum ─
    def configure(self, template):
        mu = np.array([[np.nan if v is None else v for v in row] for row in template['mu']], dtype=np.float64)
        sg = np.array([[np.nan if v is None else v for v in row] for row in template['sigma']], dtype=np.float64)
        self.template = template
        self.N = int(template.get('phases', mu.shape[0]))
        self.mu = mu
        self.sigma = sg
        self.w = np.array(template.get('weights', [1.0] * mu.shape[1]), dtype=np.float64)
        self.valid = ~np.isnan(mu)
        self.peak_phase = int(template.get('peak_phase', self.N // 2))
        # eski sablonlar yalnizca eklem listesi tasir; yenilerde 'features' var
        self.features = list(template.get('features') or template.get('joints') or JOINTS)
        self.fidx = {name: i for i, name in enumerate(self.features)}
        self._angle_cols = np.array([i for i, f in enumerate(self.features) if f in JOINT_INDEX], dtype=int)
        lead = (template.get('lead_joints') or [JOINTS[0]])[0]
        self.lead_idx = self.fidx.get(lead, 0)
        self.reset()

    @property
    def configured(self):
        return self.template is not None

    def reset(self):
        N = self.N if self.template else 1
        self.count = 0
        self.attempts = 0
        self.qualities = []
        self.last_hints = []
        self._committed = 0
        self._D = np.full(N, 1e6)
        self._D[0] = 0.0
        self._R = np.zeros(N, dtype=np.int64)
        self._qsum = np.zeros(N)
        self._qn = np.zeros(N)
        self._peak = np.zeros(N, dtype=bool)
        self._tstart = np.full(N, np.nan)
        self._last_q = np.zeros(N)
        self._last_peak = np.zeros(N, dtype=bool)
        self._last_dur = np.zeros(N)
        self._gap_since = None
        self._last_phase = 0.0
        self._prev_now = None
        self._prev_best_phase = 0.0
        self._attempt_max_phase = 0.0
        self._attempt_block_until = -1.0
        self._prev_best = 0
        self._attempt_peak_seen = False

    def export_template(self):
        return dict(self.template) if self.template else None

    def mean_quality(self):
        return float(np.mean(self.qualities)) if self.qualities else 0.0

    # ─ hesap ─
    def _feature_vec(self, features):
        a = np.full(len(self.features), np.nan)
        for name, val in (features or {}).items():
            j = self.fidx.get(name)
            if j is not None and val is not None:
                a[j] = float(val)
        return a

    def _local_cost(self, a):
        """Her faz icin agirlikli ortalama z^2 (N,), ve z matrisi (N x J)."""
        avail = ~np.isnan(a)
        mask = self.valid & avail[None, :]
        z = np.abs(self.mu - a[None, :]) / self.sigma
        z = np.where(mask, np.minimum(z, Z_CAP), np.nan)
        wmask = mask * self.w[None, :]
        wsum = wmask.sum(axis=1)
        cost = np.where(wsum > 0, np.nansum(np.nan_to_num(z) ** 2 * wmask, axis=1) / np.maximum(wsum, 1e-9), Z_CAP ** 2)
        return cost, z, int(avail.sum())

    def step(self, angles, now):
        if not self.configured:
            return self._decision(0.0, 0.0, 0.0, False, 'no_template')
        a = self._feature_vec(angles)
        if self._prev_now is None:
            self._prev_now = now
        cost, z, _n_avail = self._local_cost(a)
        n_angles = int(np.sum(~np.isnan(a[self._angle_cols])))

        # lider eklem gorunmuyorsa bekle; uzun surerse donguyu sifirla
        if np.isnan(a[self.lead_idx]) or n_angles < MIN_JOINTS:
            if self._gap_since is None:
                self._gap_since = now
            if now - self._gap_since > VISIBILITY_HOLD_SECONDS:
                self._soft_reset()
                return self._decision(self._last_phase, 0.0, 0.0, False, 'visibility')
            return self._decision(self._last_phase, 0.0, 0.0, False, 'hold')
        self._gap_since = None

        N = self.N
        D = self._D
        cand = np.stack([
            D + STAY_PENALTY,                 # kal
            np.roll(D, 1),                    # 1 ilerle
            np.roll(D, 2) + SKIP2_PENALTY,    # 2 ilerle
            np.roll(D, 3) + SKIP3_PENALTY,    # 3 ilerle
        ], axis=0)
        choice = np.argmin(cand, axis=0)                       # (N,)
        j = np.arange(N)
        pred = (j - choice) % N
        wrapped = choice > j                                   # sablon sonundan sardi
        best_prev = cand[choice, j]

        newD = COST_DECAY * best_prev + cost
        q_local = np.exp(-cost / QUALITY_SCALE)

        R = self._R[pred].copy()
        qsum = self._qsum[pred].copy()
        qn = self._qn[pred].copy()
        peak = self._peak[pred].copy()
        tstart = self._tstart[pred].copy()
        last_q = self._last_q[pred].copy()
        last_peak = self._last_peak[pred].copy()
        last_dur = self._last_dur[pred].copy()

        # sarma: onceki dongunun istatistiklerini kapat, yeniyi baslat
        if wrapped.any():
            wq = np.where(qn[wrapped] > 0, qsum[wrapped] / np.maximum(qn[wrapped], 1), 0.0)
            last_q[wrapped] = wq
            last_peak[wrapped] = peak[wrapped]
            last_dur[wrapped] = now - np.nan_to_num(tstart[wrapped], nan=now)
            R[wrapped] += 1
            qsum[wrapped] = 0.0
            qn[wrapped] = 0.0
            peak[wrapped] = False
            tstart[wrapped] = now

        # dongu baslangici: ilk kez faz 0'dan ayrilma
        starting = np.isnan(tstart) & (j > 0)
        tstart[starting] = now

        qsum += q_local
        qn += 1.0
        # tepe fazina ulasildi mi (lider eklem tolerans icinde)
        near_peak = (np.abs(j - self.peak_phase) <= max(2, N // 16))
        lead_ok = ~np.isnan(z[:, self.lead_idx]) & (z[:, self.lead_idx] <= PEAK_Z_MAX)
        peak |= near_peak & lead_ok

        self._D, self._R, self._qsum, self._qn = newD, R, qsum, qn
        self._peak, self._tstart = peak, tstart
        self._last_q, self._last_peak, self._last_dur = last_q, last_peak, last_dur

        # en iyi hucre: yol surekliligi icin histerezis — onceki en iyinin
        # ileri komsulugundaki hucre, kuresel en iyiden belirgin kotu degilse korunur
        global_best = int(np.argmin(newD))
        local_idx = (self._prev_best + np.arange(0, 4)) % N
        local_best = int(local_idx[np.argmin(newD[local_idx])])
        if newD[global_best] < newD[local_best] - SWITCH_MARGIN:
            best = global_best
            switched = True
        else:
            best = local_best
            switched = False
        self._prev_best = best
        phase = best / float(N)
        self._last_phase = phase
        quality_now = float(q_local[best])
        self._prev_now = now

        counted, reason, joint = False, None, None
        cycle_q = float(qsum[best] / max(qn[best], 1))
        prev_phase = self._prev_best_phase
        self._prev_best_phase = phase
        if R[best] > self._committed:
            pass
        elif (switched and phase < prev_phase - ATTEMPT_BACKJUMP
              and self._attempt_max_phase >= ATTEMPT_MIN_PHASE
              and now >= self._attempt_block_until):
            # hizalama yolu geriye atladi: yarim kalan deneme.
            # neden: lider eklem tepe fazina ulasmissa 'form', ulasmamissa 'amplitude'
            self.attempts += 1
            reason = 'form' if self._attempt_peak_seen else 'amplitude'
            self._attempt_max_phase = 0.0
            self._attempt_peak_seen = False
            self._attempt_block_until = now + ATTEMPT_COOLDOWN
            return self._decision(phase, quality_now, cycle_q, False, reason, None, z[best])
        elif switched:
            # ileri yonlu yol degisimi: deneme izini yeni konumdan baslat
            self._attempt_max_phase = phase
            self._attempt_peak_seen = bool(peak[best])
        if now >= self._attempt_block_until:
            self._attempt_max_phase = max(self._attempt_max_phase, phase)
            self._attempt_peak_seen = self._attempt_peak_seen or bool(peak[best])
        if R[best] > self._committed:
            self._attempt_max_phase = 0.0
            self._attempt_peak_seen = False
            self._committed = int(R[best])
            cq = float(last_q[best])
            dur = float(last_dur[best])
            if not last_peak[best]:
                reason = 'amplitude'
                self.attempts += 1
            elif dur < MIN_REP_SECONDS:
                reason = 'too_short'
            elif dur > MAX_REP_SECONDS:
                reason = 'too_long'
                self.attempts += 1
            elif cq < REP_CYCLE_QUALITY:
                reason = 'form'
                self.attempts += 1
            else:
                counted = True
                self.count += 1
                self.qualities.append(cq)
            cycle_q = cq

        self.last_hints = []
        return self._decision(phase, quality_now, cycle_q, counted, reason, joint, z[best])

    def _soft_reset(self):
        N = self.N
        self._D = np.full(N, 1e6)
        self._D[0] = 0.0
        self._R[:] = self._committed
        self._qsum[:] = 0.0
        self._qn[:] = 0.0
        self._peak[:] = False
        self._tstart[:] = np.nan
        self._gap_since = None
        self._prev_best_phase = 0.0
        self._attempt_max_phase = 0.0
        self._attempt_block_until = -1.0
        self._prev_best = 0
        self._attempt_peak_seen = False

    def joint_status(self, zrow):
        """z-skor satirindan eklem ve uc nokta durumu ile ipuclari."""
        status, feedback = {}, []
        if zrow is None:
            return status, feedback
        for name in JOINTS:
            j = self.fidx.get(name)
            if j is None:
                continue
            jz = zrow[j]
            if np.isnan(jz):
                continue
            if jz >= Z_WARN:
                status[name] = 'error'
                feedback.append(f"{JOINT_NAMES_TR[name]}: referanstan sapma ({jz:.1f} sigma)")
            elif jz >= Z_OK:
                status[name] = 'warning'
                feedback.append(f"{JOINT_NAMES_TR[name]}: doktor gibi yapin")
            else:
                status[name] = 'ok'
        for ep in ENDPOINTS:
            cols = [self.fidx[f'{ep}_{c}'] for c in 'xyz' if f'{ep}_{c}' in self.fidx]
            if not cols:
                continue
            vals = zrow[cols]
            if np.all(np.isnan(vals)):
                continue
            ez = float(np.nanmax(vals))
            if ez >= Z_WARN:
                status[ep] = 'error'
                feedback.append(f"{ENDPOINT_NAMES_TR[ep]}: konum referanstan sapiyor ({ez:.1f} sigma)")
            elif ez >= Z_OK:
                status[ep] = 'warning'
                feedback.append(f"{ENDPOINT_NAMES_TR[ep]}: konumu doktor gibi tutun")
            else:
                status[ep] = 'ok'
        return status, feedback

    def _decision(self, phase, quality, cycle_quality, counted, reason, joint=None, zrow=None):
        return {
            'counted': counted,
            'phase': round(float(phase), 4),
            'quality': round(float(quality), 4),
            'cycle_quality': round(float(cycle_quality), 4),
            'reason': reason,
            'joint': joint,
            'z': zrow,
            'count': self.count,
            'attempts': self.attempts,
        }
