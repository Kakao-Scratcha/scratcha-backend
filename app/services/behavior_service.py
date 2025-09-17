# app/services/behavior_service.py

import os
import json
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

import numpy as np
import torch
import torch.nn as nn
from threading import Lock

# 로거 설정
logger = logging.getLogger(__name__)

# ====== Model (lazy loader + shared entrypoints) ======


class CNN1D(nn.Module):
    def __init__(self, in_ch=7, c1=96, c2=192, dropout=0.2, input_bn=True):
        super().__init__()
        self.input_bn = nn.BatchNorm1d(in_ch) if input_bn else nn.Identity()
        self.feat = nn.Sequential(
            nn.Conv1d(in_ch, c1, kernel_size=7, padding=3),
            nn.BatchNorm1d(c1),
            nn.ReLU(inplace=True),
            nn.Conv1d(c1, c2, kernel_size=5, padding=2),
            nn.BatchNorm1d(c2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.head = nn.Linear(c2, 1)

    def forward(self, x):  # (B,7,T)
        x = self.input_bn(x)
        h = self.feat(x)
        h = h.mean(dim=-1)
        return self.head(h).squeeze(1)


# 경로 설정
# 이 서비스 파일의 위치를 기준으로 app 폴더를 찾습니다.
# /app/app/services/behavior_service.py -> /app/app
APP_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = APP_DIR / "artifacts"
BEST_PT = ARTIFACTS_DIR / "cnn" / "best.pt"
THR_JSON = ARTIFACTS_DIR / "cnn" / "thresholds.json"
CALIB_JSON = ARTIFACTS_DIR / "cnn" / "calibration.json"

_MODEL: Optional[nn.Module] = None
_THRESHOLD: Optional[float] = None
_DEVICE = "cpu"
_MODEL_LOCK = Lock()


def _load_threshold_once() -> float:
    global _THRESHOLD
    if _THRESHOLD is not None:
        return _THRESHOLD
    try:
        with open(THR_JSON, "r", encoding="utf-8") as f:
            _THRESHOLD = float(json.load(f).get("val_threshold", 0.5))
    except Exception as e:
        logger.info(f"[경고] thresholds.json 로드 실패: {e}")
        _THRESHOLD = 0.5
    return _THRESHOLD


def get_threshold() -> float:
    return _load_threshold_once()


def get_model() -> Optional[nn.Module]:
    """필요 시점에만 안전하게 로딩. 실패해도 다음 요청에서 재시도."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        try:
            m = CNN1D(in_ch=7, c1=96, c2=192, dropout=0.2, input_bn=True)
            state = torch.load(BEST_PT, map_location=_DEVICE)
            m.load_state_dict(state, strict=True)
            m.eval()
            _MODEL = m
            logger.info(f"행동검증모델(best.pt) 로드 완료: {BEST_PT}")
        except Exception as e:
            logger.info(f"행동검증모델(best.pt) 로드 실패: {e}")
            _MODEL = None
        return _MODEL


# ====== Calibration (temperature / platt) ======
_CALIB = None
_CALIB_MTIME = None


def _load_calibration():
    """
    calibration.json mtime을 보고 자동 리로드.
    지원: {"type":"temperature","T":...}  |  {"type":"platt","a":...,"b":...}
    """
    global _CALIB, _CALIB_MTIME
    try:
        st = CALIB_JSON.stat()
        if _CALIB is not None and _CALIB_MTIME == st.st_mtime:
            return _CALIB  # 캐시 유효
        with open(CALIB_JSON, "r", encoding="utf-8") as f:
            obj = json.load(f)
        t = str(obj.get("type", "")).lower()
        if t == "temperature":
            _CALIB = ("temperature", float(obj["T"]))
        elif t == "platt":
            _CALIB = ("platt", float(obj["a"]), float(obj["b"]))
        else:
            _CALIB = None
        _CALIB_MTIME = st.st_mtime
    except Exception:
        _CALIB = None
        _CALIB_MTIME = None
    return _CALIB


# ====== Temperature scaling =====
LOGIT_TEMPERATURE = float(os.getenv("LOGIT_TEMPERATURE", "2.0"))

# ====== 전처리: behavior_features.py 로직 ======

# ---------- ROI 유틸 ----------


def _to_rect(d):
    try:
        L, T, W, H = float(d.get("left")), float(
            d.get("top")), float(d.get("w")), float(d.get("h"))
        if W <= 0 or H <= 0:
            return None
        return (L, T, W, H)
    except Exception:
        return None


def _roi_rects(meta: Any) -> Tuple[Optional[Tuple[float, float, float, float]], Optional[Tuple[float, float, float, float]]]:
    """
    rect_track:  정규화 및 모델 입력 OOB(=canvas 기준)   -> 폴백 금지
    rect_oob:    통계용 wrapper 기준 (없으면 None)
    """
    # meta가 dict일 경우를 대비하여 getattr 대신 .get() 사용
    roi_map = meta.get("roi_map", {}) or {}
    rect_canvas = _to_rect(roi_map.get("canvas-container")
                           ) if roi_map.get("canvas-container") else None
    rect_wrap = _to_rect(roi_map.get("scratcha-container")
                         ) if roi_map.get("scratcha-container") else None
    # 🔒 canvas 기준을 강제: canvas가 없으면 track 없음으로 간주
    rect_track = rect_canvas
    rect_oob = rect_wrap
    logger.info(
        f"_roi_rects 결과: rect_track={rect_track}, rect_oob={rect_oob}")
    return rect_track, rect_oob

# ---------- 이벤트 평탄화 ----------


def _flatten_events(meta: Any, events: List[Any]):
    out = []
    for ev in events:
        et = getattr(ev, "type", None) or (
            ev.get("type") if isinstance(ev, dict) else None)
        if et in ("moves", "moves_free"):
            p = getattr(ev, "payload", None) or (
                ev.get("payload") if isinstance(ev, dict) else None)
            if not p:
                continue
            base = int(getattr(p, "base_t", 0) or (
                p.get("base_t") if isinstance(p, dict) else 0) or 0)
            dts = list(getattr(p, "dts", []) or (
                p.get("dts") if isinstance(p, dict) else []) or [])
            xs = list(getattr(p, "xrs", []) or (
                p.get("xrs") if isinstance(p, dict) else []) or [])
            ys = list(getattr(p, "yrs", []) or (
                p.get("yrs") if isinstance(p, dict) else []) or [])
            t = base
            n = min(len(dts), len(xs), len(ys))
            for i in range(n):
                out.append((t, float(xs[i]), float(ys[i])))
                dt = int(dts[i]) if int(dts[i]) > 0 else 1
                t += dt
        elif et in ("pointerdown", "pointerup", "click"):
            t = (getattr(ev, "t", None) if not isinstance(
                ev, dict) else ev.get("t"))
            xr = (getattr(ev, "x_raw", None) if not isinstance(
                ev, dict) else ev.get("x_raw"))
            yr = (getattr(ev, "y_raw", None) if not isinstance(
                ev, dict) else ev.get("y_raw"))
            if t is None or xr is None or yr is None:
                continue
            out.append((int(t), float(xr), float(yr)))
    out.sort(key=lambda x: x[0])
    logger.info(f"_flatten_events 결과: {len(out)}개의 포인트, 첫 5개: {out[:5]}")
    return out

# ---------- 시간 단위 보정 (sec/ms/us → ms) ----------


def _time_scale_to_ms(t: np.ndarray) -> Tuple[np.ndarray, str]:
    """
    규칙 (build_dataset.py와 동일):
    - 이미 ms: rng>=1000ms 또는 med_dt>=5ms → 그대로
    - 초 단위: 0.2<=med_dt<=5.0 and rng<=600 → *1000
    - 프레임 인덱스(60/30Hz): 0.8<=med_dt<=1.2 → *16  (보수적 16ms)
    - 범위가 너무 작음(rng<100ms): 인덱스 재생성 → idx*16
    - 그 외: ms로 간주 (fallback)
    """
    if t.size < 2:
        return t, "time_ok_len1"
    t = t.astype(np.float64)
    rng = float(t[-1] - t[0])
    dt = np.diff(t)
    med_dt = float(np.median(dt)) if dt.size else 0.0

    if rng >= 1000.0 or med_dt >= 5.0:
        return t, "time_ms"
    if 0.2 <= med_dt <= 5.0 and rng <= 600.0:
        return t * 1000.0, "time_seconds_scaled_ms"
    if 0.8 <= med_dt <= 1.2:
        return t * 16.0, "time_frames_scaled_ms"
    if rng < 100.0:
        idx = np.arange(len(t), dtype=np.float64)
        return idx * 16.0, "time_reindexed_16ms"
    return t, "time_ms_fallback"


def _norm_xy(x_raw: float, y_raw: float, rect: Tuple[float, float, float, float]):
    L, T, W, H = rect
    xr = (x_raw - L) / max(1.0, W)
    yr = (y_raw - T) / max(1.0, H)
    oob = 1 if (xr < 0 or xr > 1 or yr < 0 or yr > 1) else 0
    x = min(1.0, max(0.0, xr))
    y = min(1.0, max(0.0, yr))
    return x, y, oob

# ---------- 특징 구성 (dt 기반, 모델 입력 oob=canvas 기준) ----------


def build_window_7ch(meta: Any, events: List[Any], T: int = 300):
    """
    반환: (X, raw_len, has_track, has_wrap, oob_canvas_rate, oob_wrapper_rate)
      - X: (T,7) float32, 채널=[x,y,vx,vy,speed,accel,oob_canvas]
    """
    rect_track, rect_oob = _roi_rects(meta)
    if rect_track is None:
        logger.info(
            f"build_window_7ch: rect_track이 None이므로 전처리 건너뛰기. meta: {meta}")
        return None, 0, False, (rect_oob is not None), 0.0, 0.0, 0.0

    pts = _flatten_events(meta, events)
    if not pts:
        logger.info(
            f"build_window_7ch: 평탄화된 이벤트(pts)가 없으므로 전처리 건너뛰기. events: {events}")
        return None, 0, True, (rect_oob is not None), 0.0, 0.0, 0.0

    # 1) 정규화 + OOB (canvas 기준)
    xs, ys, oobs_canvas, oobs_wrap, ts = [], [], [], [], []
    for t, xr, yr in pts:
        x1, y1, oob_canvas = _norm_xy(xr, yr, rect_track)  # ← 항상 canvas 기준
        xs.append(x1)
        ys.append(y1)
        oobs_canvas.append(oob_canvas)
        ts.append(float(t))

        if rect_oob is not None:
            _, _, oob_wrap = _norm_xy(xr, yr, rect_oob)    # 통계용 wrapper
        else:
            oob_wrap = 0  # wrapper가 없으면 0으로
        oobs_wrap.append(oob_wrap)

    xs = np.asarray(xs, dtype=np.float32)
    ys = np.asarray(ys, dtype=np.float32)
    oobs_canvas = np.asarray(oobs_canvas, dtype=np.float32)
    oobs_wrap = np.asarray(oobs_wrap, dtype=np.float32)
    ts = np.asarray(ts, dtype=np.float64)
    ts, _ = _time_scale_to_ms(ts)  # 2) 시간 보정(ms)

    # 3) dt (sec)
    dt_ms = np.diff(ts, prepend=ts[0])
    dt_ms = np.clip(dt_ms, 1e-3, None)
    dt_s = dt_ms / 1000.0

    # 4) vx, vy, speed, accel
    if len(xs) < 2:
        vx = np.zeros_like(xs)
        vy = np.zeros_like(ys)
        speed = np.zeros_like(xs)
        accel = np.zeros_like(xs)
    else:
        dx = np.diff(xs, prepend=xs[0])
        dy = np.diff(ys, prepend=ys[0])
        vx = dx / dt_s
        vy = dy / dt_s
        speed = np.sqrt(vx*vx + vy*vy)
        accel = np.diff(speed, prepend=speed[0]) / dt_s

    # 5) 모델 입력: [x, y, vx, vy, speed, accel, oob_canvas]
    X = np.stack([xs, ys, vx, vy, speed, accel, oobs_canvas],
                 axis=1).astype(np.float32)
    raw_len = X.shape[0]

    # Calculate total distance
    total_distance = 0.0
    if raw_len > 1:
        total_distance = float(np.sum(np.sqrt(np.diff(xs)**2 + np.diff(ys)**2)))

    # 6) 길이 정규화
    if raw_len < T:
        X = np.concatenate(
            [X, np.zeros((T - raw_len, X.shape[1]), np.float32)], axis=0)
    elif raw_len > T:
        X = X[-T:, :]

    # 7) 통계
    oob_canvas_rate = float(np.mean(oobs_canvas > 0.5)
                            ) if oobs_canvas.size else 0.0
    oob_wrapper_rate = float(np.mean(oobs_wrap > 0.5)
                             ) if oobs_wrap.size else 0.0
    return X, raw_len, True, (rect_oob is not None), oob_canvas_rate, oob_wrapper_rate, total_distance, has_move_events


def seq_stats(X, raw_len: int, has_track: bool, has_wrap: bool, oob_canvas_rate: float, oob_wrap_rate: float, total_distance: float):
    if X is None or X.size == 0:
        return {
            "oob_rate_canvas": 0.0,
            "oob_rate_wrapper": 0.0,
            "speed_mean": 0.0,
            "n_events": 0,
            "roi_has_canvas": has_track,
            "roi_has_wrapper": has_wrap,
        }
    return {
        "oob_rate_canvas": float(oob_canvas_rate),
        "oob_rate_wrapper": float(oob_wrap_rate),
        "speed_mean": float(np.mean(X[:, 4])),
        "n_events": int(raw_len),
        "roi_has_canvas": has_track,
        "roi_has_wrapper": has_wrap,
        "total_distance": total_distance,
    }

# ====== Inference Entrypoint ======


def run_behavior_verification(meta: Dict[str, Any], events: List[Dict[str, Any]]):
    model = get_model()
    if model is None:
        logger.error("행동 검증 모델이 로드되지 않았습니다.")
        return {"ok": False, "error": "model not loaded"}

    # (전처리)
    X, raw_len, has_track, has_wrap, oob_c, oob_w, total_distance = build_window_7ch(
        meta, events, T=300)
    if X is None:
        logger.info("특징 추출 결과가 None입니다. 추론을 건너뜁니다.")
        return {"ok": False, "error": "empty or invalid events/roi"}

    # (추론)
    xt = torch.from_numpy(np.transpose(X, (1, 0))).unsqueeze(
        0).float()  # (1,7,300)
    with torch.no_grad():
        logit = model(xt).item()

    # (후처리) Calibration 우선순위: temperature → platt
    calib = _load_calibration()
    if calib and calib[0] == "temperature":
        T = max(1.0, float(calib[1]))   # ← 안전: 최소 1.0로 고정
        z = logit / T
    elif calib and calib[0] == "platt":
        a, b = float(calib[1]), float(calib[2])
        z = a * logit + b
    else:
        T = 2.0  # 기본 Temperature
        z = logit / T

    z_raw = float(z)
    z_clip = float(np.clip(z_raw, -3.0, 3.0))  # 시그모이드 전 클립
    prob = float(1.0 / (1.0 + np.exp(-z_clip)))

    thr = float(get_threshold())
    verdict = "bot" if prob >= thr else "human"

    return {
        "ok": True,
        "model": "cnn",
        "bot_prob": prob,
        "threshold": thr,
        "verdict": verdict,
        "stats": seq_stats(X, raw_len, has_track, has_wrap, oob_c, oob_w, total_distance),
    }
