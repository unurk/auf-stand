"""WHOOP API Client — holt Recovery, Sleep, Workout und Cycle-Daten."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from .auth import get_valid_token

_API = "https://api.prod.whoop.com/developer/v1"

SPORT_NAMES: dict[int, str] = {
    0: "Aktivität",
    1: "Laufen",
    16: "Baseball",
    17: "Basketball",
    18: "Rudern",
    19: "Boxen",
    21: "Crossfit",
    22: "Radfahren",
    27: "Fußball",
    28: "Golf",
    30: "Handball",
    31: "Eishockey",
    33: "Kampfsport",
    35: "Krafttraining",
    38: "Mountainbike",
    40: "Powerlifting",
    43: "Ski",
    44: "Schwimmen",
    45: "Squash",
    46: "Stairmaster",
    50: "Tennis",
    51: "Triathlon",
    56: "Yoga",
    57: "Klettern",
    59: "HIIT",
    60: "Tanzen",
    63: "Crosstrainer",
    64: "Pilates",
    70: "Spazierengehen",
    71: "Wandern",
    72: "Stretching",
    74: "Functional Fitness",
    230: "Meditation",
}


@dataclass
class WorkoutRecord:
    sport: str
    start: str
    end: str
    strain: Optional[float]
    avg_hr: Optional[int]
    max_hr: Optional[int]
    kcal: Optional[float]


@dataclass
class DayData:
    date: str  # YYYY-MM-DD
    # Recovery
    recovery_score: Optional[int] = None
    hrv_ms: Optional[float] = None
    rhr: Optional[int] = None
    spo2: Optional[float] = None
    skin_temp: Optional[float] = None
    # Sleep (Hauptschlaf)
    sleep_hours: Optional[float] = None
    sleep_performance: Optional[int] = None
    deep_sleep_hours: Optional[float] = None
    rem_hours: Optional[float] = None
    light_sleep_hours: Optional[float] = None
    sleep_efficiency: Optional[int] = None
    sleep_consistency: Optional[int] = None
    sleep_disturbances: Optional[int] = None
    sleep_cycles: Optional[int] = None
    respiratory_rate: Optional[float] = None
    sleep_needed_hours: Optional[float] = None
    # Cycle / Strain
    day_strain: Optional[float] = None
    day_kcal: Optional[float] = None
    # Workouts
    workouts: list[WorkoutRecord] = field(default_factory=list)


def _get(path: str, params: dict) -> dict:
    token = get_valid_token()
    resp = requests.get(
        f"{_API}{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _paginate(path: str, start: str, end: str) -> list[dict]:
    records: list[dict] = []
    params: dict = {"start": start, "end": end, "limit": 25}
    while True:
        data = _get(path, params)
        records.extend(data.get("records", []))
        nxt = data.get("next_token")
        if not nxt:
            break
        params = {"nextToken": nxt, "limit": 25}
    return records


def _ms_to_h(ms: int) -> float:
    return round(ms / 3_600_000, 2)


def fetch_days(days: int = 7) -> list[DayData]:
    """Gibt die letzten `days` Tage als DayData-Liste zurück (ältestes zuerst)."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    end = now.isoformat()

    cycles_raw = _paginate("/cycle", start, end)
    recovery_raw = _paginate("/recovery", start, end)
    sleep_raw = _paginate("/sleep", start, end)
    workout_raw = _paginate("/workout", start, end)

    rec_by_cycle: dict[int, dict] = {
        r["cycle_id"]: r for r in recovery_raw if r.get("score_state") == "SCORED"
    }

    sleep_by_id: dict[int, dict] = {
        s["id"]: s for s in sleep_raw if s.get("score_state") == "SCORED" and not s.get("nap")
    }

    workouts_by_date: dict[str, list[WorkoutRecord]] = {}
    for w in workout_raw:
        if w.get("score_state") != "SCORED":
            continue
        sc = w.get("score", {})
        date_key = w["start"][:10]
        wo = WorkoutRecord(
            sport=SPORT_NAMES.get(w.get("sport_id", 0), "Aktivität"),
            start=w["start"],
            end=w["end"],
            strain=sc.get("strain"),
            avg_hr=sc.get("average_heart_rate"),
            max_hr=sc.get("max_heart_rate"),
            kcal=round(sc["kilojoule"] / 4.184) if sc.get("kilojoule") else None,
        )
        workouts_by_date.setdefault(date_key, []).append(wo)

    days_map: dict[str, DayData] = {}
    for c in cycles_raw:
        if c.get("score_state") != "SCORED":
            continue
        date_key = c["start"][:10]
        sc = c.get("score", {})
        day = DayData(
            date=date_key,
            day_strain=sc.get("strain"),
            day_kcal=round(sc["kilojoule"] / 4.184) if sc.get("kilojoule") else None,
            workouts=workouts_by_date.get(date_key, []),
        )

        rec = rec_by_cycle.get(c["id"])
        if rec:
            rs = rec.get("score", {})
            day.recovery_score = rs.get("recovery_score")
            day.hrv_ms = rs.get("hrv_rmssd_milli")
            day.rhr = rs.get("resting_heart_rate")
            day.spo2 = rs.get("spo2_percentage")
            day.skin_temp = rs.get("skin_temp_celsius")

            sleep = sleep_by_id.get(rec.get("sleep_id", 0))
            if sleep:
                ss = sleep.get("score", {})
                stages = ss.get("stage_summary", {})
                needed = ss.get("sleep_needed", {})
                total_sleep_ms = (
                    stages.get("total_in_bed_time_milli", 0)
                    - stages.get("total_awake_time_milli", 0)
                )
                needed_ms = sum(
                    needed.get(k, 0)
                    for k in (
                        "baseline_milli",
                        "need_from_sleep_debt_milli",
                        "need_from_recent_strain_milli",
                    )
                )
                day.sleep_hours = _ms_to_h(total_sleep_ms) if total_sleep_ms else None
                day.deep_sleep_hours = _ms_to_h(stages.get("total_slow_wave_sleep_time_milli", 0)) or None
                day.rem_hours = _ms_to_h(stages.get("total_rem_sleep_time_milli", 0)) or None
                day.light_sleep_hours = _ms_to_h(stages.get("total_light_sleep_time_milli", 0)) or None
                day.sleep_disturbances = stages.get("disturbance_count")
                day.sleep_cycles = stages.get("sleep_cycle_count")
                day.sleep_performance = ss.get("sleep_performance_percentage")
                day.sleep_efficiency = ss.get("efficiency_percentage")
                day.sleep_consistency = ss.get("sleep_consistency_percentage")
                day.respiratory_rate = ss.get("respiratory_rate")
                day.sleep_needed_hours = _ms_to_h(needed_ms) if needed_ms else None

        days_map[date_key] = day

    return sorted(days_map.values(), key=lambda d: d.date)
