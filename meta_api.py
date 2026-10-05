"""Metadata + matching endpoints for the yowes web UI.

Added endpoints (mounted into webui.py):
  GET  /api/meta        -> per-country: display name, doc types, schools, name lists, positions
  POST /api/resolve     -> match a first/last name to the best country
"""
import sys
from pathlib import Path

YOWES_DIR = Path("/opt/yowes")
if str(YOWES_DIR) not in sys.path:
    sys.path.insert(0, str(YOWES_DIR))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from countries import get_country, list_countries

router = APIRouter()


def _country_meta(code: str) -> dict:
    gen = get_country(code)()
    mod = __import__(f"countries.{code}", fromlist=["*"])
    first = last = positions = []
    for attr in dir(mod):
        if attr.endswith("FIRST_NAMES"):
            first = list(getattr(mod, attr))
        elif attr.endswith("LAST_NAMES"):
            last = list(getattr(mod, attr))
        elif attr.endswith("TEACHING_POSITIONS"):
            positions = list(getattr(mod, attr))
    return {
        "code": code,
        "name": gen.get_country_name(),
        "document_types": gen.get_document_types(),
        "schools": [s["name"] for s in gen.schools],
        "first_names": first,
        "last_names": last,
        "positions": positions,
    }


@router.get("/api/meta")
def api_meta():
    return {c: _country_meta(c) for c in list_countries()}


class ResolveReq(BaseModel):
    first_name: str
    last_name: str
    gender: str = "Random"


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s.strip().lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


@router.post("/api/resolve")
def api_resolve(req: ResolveReq):
    """Score the given name against every country's name lists and return the
    best matches with a consistent random identity profile."""
    import random

    first = _norm(req.first_name)
    last = _norm(req.last_name)
    if not first or not last:
        raise HTTPException(400, "Nama depan dan belakang wajib diisi.")

    scored = []
    for code in list_countries():
        m = _country_meta(code)
        firsts = {_norm(n) for n in m["first_names"]}
        lasts = {_norm(n) for n in m["last_names"]}
        score = (2 if first in firsts else 0) + (2 if last in lasts else 0)
        # partial credit: name starts with / contains a listed name
        if score == 0:
            if any(first.startswith(f) and len(f) >= 3 for f in firsts):
                score += 1
            if any(last.startswith(l) and len(l) >= 3 for l in lasts):
                score += 1
        scored.append((score, code, m))

    scored.sort(key=lambda t: (-t[0], t[1]))
    best_score, best_code, best = scored[0]
    if best_score == 0:
        # no match anywhere: pick a random country instead of always the first
        best_score, best_code, best = random.choice(scored)

    rnd = random.Random(f"{req.first_name}|{req.last_name}".lower())
    position = rnd.choice(best["positions"]) if best["positions"] else "Teacher"
    birth_year = rnd.randint(1975, 2000)
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    dob = f"{rnd.randint(1, 28)} {rnd.choice(months)} {birth_year}"

    return {
        "country": best_code,
        "country_name": best["name"],
        "match_score": best_score,
        "matched": best_score > 0,
        "candidates": [
            {"code": c, "name": m["name"], "score": s}
            for s, c, m in scored[:4] if s > 0
        ],
        "profile": {
            "position": position,
            "date_of_birth": dob,
            "gender": req.gender if req.gender != "Random" else rnd.choice(["Male", "Female"]),
            "school_name": rnd.choice(best["schools"]) if best["schools"] else "",
        },
        "document_types": best["document_types"],
    }
