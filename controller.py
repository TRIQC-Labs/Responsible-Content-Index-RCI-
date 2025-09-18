# controller.py
from __future__ import annotations
import json, hashlib, secrets
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from typing import Optional
from progress import Reporter

# --- Your lens callers ---
from module_exclusionary import run_exclusionary_analysis
from module_misinformation import run_misinformation_analysis
from module_bias import run_bias_analysis

# --- Config ---
POLICY_VERSION = "DEM_v1.3"
MODEL_VERSIONS = {
    "origin": "origin-detector_v0.7",
    "bias_fairness": "bf-evaluator_v2.4",
    "exclusionary_language": "el-scanner_v1.9",
    "misinformation": "mi-checker_v1.6",
}
DEFAULT_THRESHOLDS = {
    "bias_fairness": 0.65,
    "exclusionary_language": 0.65,
    "misinformation_risk": 0.40,
}
SEVERITY_TO_SUMMARY = {
    "None":   "No material subgroup harms detected",
    "Low":    "Moderate-severity phrase detected",
    "Medium": "Risk phrase detected",
    "High":   "Severe violation detected — adjustment mandatory",
}
MISINFO_SUMMARY = {
    False: "No unverifiable or high-risk claims",
    True:  "One or more unverifiable or high-risk claims found",
}

# --- Helpers ---
def _say(r: Optional[Reporter], event: str, **data):
    if r: r.emit(event, **data)

def now_iso_pst() -> str:
    # Avoid dependency on zoneinfo; render offset on UTC
    # If you want America/Los_Angeles specifically, set tzinfo via zoneinfo.
    return datetime.now(timezone.utc).astimezone().isoformat()

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def short_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(3)}"  # ~16M space

def clamp01(x: float, ndigits: Optional[int] = None) -> float:
    x = max(0.0, min(1.0, float(x)))
    return round(x, ndigits) if ndigits is not None else x

def norm_int100(x: Any) -> int:
    try:
        v = int(round(float(x)))
    except Exception:
        v = 0
    return max(0, min(100, v))

def _pass_from(severity: str, risk_score: float, risk_threshold: float) -> bool:
    return severity in {"None", "Low"} and risk_score < risk_threshold

def _ensure_dict(x: Any) -> Dict[str, Any]:
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return {}
    return {}

def _unwrap_envelope(result: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Accept either {key: {...}} or bare {...} and return inner dict."""
    if key in result and isinstance(result[key], dict):
        return result[key]
    return result

# --- Normalizers: map module outputs to your certificate schema exactly ---
def normalize_bias_fairness(raw: Dict[str, Any], risk_threshold: float) -> Dict[str, Any]:
    bf = _unwrap_envelope(_ensure_dict(raw), "bias_fairness")
    severity = bf.get("severity", "None")
    risk_score = clamp01(bf.get("risk_score", 0.0), 4)
    confidence = norm_int100(bf.get("confidence", 0))
    summary = bf.get("summary") or SEVERITY_TO_SUMMARY.get(severity, SEVERITY_TO_SUMMARY["None"])
    pass_flag = bf.get("pass")
    if pass_flag is None:
        pass_flag = _pass_from(severity, risk_score, risk_threshold)
    return {
        "pass": bool(pass_flag),
        "summary": summary,
        "severity": severity,
        "confidence": confidence,
        "risk_score": risk_score,
        "risk_threshold": clamp01(bf.get("risk_threshold", risk_threshold), 2),
        "bias_type": bf.get("bias_type"),
        "affected_group": bf.get("affected_group"),
        "reasoning": bf.get("reasoning") or "",
    }

def normalize_exclusionary(raw: Dict[str, Any], risk_threshold: float) -> Dict[str, Any]:
    ex = _unwrap_envelope(_ensure_dict(raw), "exclusionary_language")
    severity = ex.get("severity", "None")
    risk_score = clamp01(ex.get("risk_score", 0.0), 4)
    confidence = norm_int100(ex.get("confidence", 0))
    summary = ex.get("summary") or SEVERITY_TO_SUMMARY.get(severity, SEVERITY_TO_SUMMARY["None"])
    pass_flag = ex.get("pass")
    if pass_flag is None:
        pass_flag = _pass_from(severity, risk_score, risk_threshold)

    # groups (dedup, max 3)
    groups = ex.get("affected_groups")
    if isinstance(groups, list):
        seen = []
        for g in groups:
            if isinstance(g, str) and g not in seen:
                seen.append(g)
        groups = seen[:3]
    else:
        groups = None

    # spans (sanitize types)
    spans_in = ex.get("spans", [])
    spans_out = []
    if isinstance(spans_in, list):
        for i, sp in enumerate(spans_in):
            if not isinstance(sp, dict):
                continue
            spans_out.append({
                "text": sp.get("text", ""),
                "char_start": int(sp.get("char_start", 0)),
                "char_end": int(sp.get("char_end", 0)),
                "policy_code": sp.get("policy_code", f"EX-{i+1:03d}"),
                "suggested_rewrite": sp.get("suggested_rewrite", "")
            })

    return {
        "pass": bool(pass_flag),
        "summary": summary,
        "reasoning": ex.get("reasoning") or "",
        "severity": severity,
        "confidence": confidence,
        "risk_score": risk_score,
        "risk_threshold": clamp01(ex.get("risk_threshold", risk_threshold), 2),
        "exclusionary_type": ex.get("exclusionary_type"),
        "affected_groups": groups,
        "spans": spans_out,
    }

def normalize_misinformation(raw: Dict[str, Any], risk_threshold: float) -> Dict[str, Any]:
    mi = _unwrap_envelope(_ensure_dict(raw), "misinformation_risk")
    severity = mi.get("severity", "None")
    risk_score = clamp01(mi.get("risk_score", 0.0), 4)
    confidence = norm_int100(mi.get("confidence", 0))
    pass_flag = mi.get("pass")
    if pass_flag is None:
        pass_flag = _pass_from(severity, risk_score, risk_threshold)
    summary = mi.get("summary") or MISINFO_SUMMARY[not pass_flag]

    # flagged_claims (sanitize)
    flagged = []
    for fc in mi.get("flagged_claims", []) or []:
        if not isinstance(fc, dict):
            continue
        flagged.append({
            "claim_text": fc.get("claim_text", ""),
            "char_start": int(fc.get("char_start", 0)),
            "char_end": int(fc.get("char_end", 0)),
            "claim_type": fc.get("claim_type"),
            "verdict": fc.get("verdict"),
            "claim_risk": clamp01(fc.get("claim_risk", 0.0), 4),
            "evidence_used": fc.get("evidence_used", [])[:10] if isinstance(fc.get("evidence_used"), list) else [],
            "evidence_notes": fc.get("evidence_notes", "")
        })

    return {
        "pass": bool(pass_flag),
        "summary": summary,
        "severity": severity,
        "confidence": confidence,
        "risk_score": risk_score,
        "risk_threshold": clamp01(mi.get("risk_threshold", risk_threshold), 2),
        "flagged_claims": flagged,
        "suggested_queries": mi.get("suggested_queries", [])[:5] if isinstance(mi.get("suggested_queries"), list) else [],
        "reasoning": mi.get("reasoning") or ""
    }

# --- Signature (placeholder) ---
def sign_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Plug in real Ed25519 signing later. For now, include the alg and a null sig.
    return {"alg": "ed25519", "sig": None}

# --- Public API ---
def evaluate_text(text: str, reporter: Optional[Reporter] = None) -> Dict[str, Any]:
    _say(reporter, "start", message="Beginning evaluation", chars=len(text))

    # Call modules
    _say(reporter, "lens_start", lens="bias_fairness", message="Running bias/fairness")
    bias_raw = run_bias_analysis(text)
    _say(reporter, "lens_done", lens="bias_fairness")
    _say(reporter, "lens_start", lens="exclusionary_language", message="Running exclusionary language")
    exclusionary_raw = run_exclusionary_analysis(text)
    _say(reporter, "lens_done", lens="exclusionary_language")
    _say(reporter, "lens_start", lens="misinformation_risk", message="Running misinformation risk")
    misinformation_raw = run_misinformation_analysis(text)
    _say(reporter, "lens_done", lens="misinformation_risk")

    _say(reporter, "normalize", message="Putting together results nicely")
    # Normalize to certificate schema
    bf = normalize_bias_fairness(bias_raw, DEFAULT_THRESHOLDS["bias_fairness"])
    el = normalize_exclusionary(exclusionary_raw, DEFAULT_THRESHOLDS["exclusionary_language"])
    mi = normalize_misinformation(misinformation_raw, DEFAULT_THRESHOLDS["misinformation_risk"])

    _say(reporter, "assemble", message="Assembling certificate")
    # Assemble certificate
    report = {
        "report_id": short_id("rep"),
        "created_at": now_iso_pst(),
        "policy_version": POLICY_VERSION,
        "input_sha256": sha256_hex(text),
        "models": {
            "origin": MODEL_VERSIONS["origin"],
            "bias_fairness": MODEL_VERSIONS["bias_fairness"],
            "exclusionary_language": MODEL_VERSIONS["exclusionary_language"],
            "misinformation": MODEL_VERSIONS["misinformation"],
        },
        "signature": {"alg": "ed25519", "sig": None},  # will be filled just below
        "checks": {
            "origin": {
                "status": "not_evaluated",
                "note": "Leave alone for now; will be added later."
            },
            "bias_fairness": bf,
            "exclusionary_language": el,
            "misinformation_risk": mi
        },
        "audit": {
            "prompt_hash": None,  # optional: pass concatenated prompts and hash upstream
            "run_id": f"run_{datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')}_{secrets.token_hex(2)}",
            "deterministic_seed": 1337,
            "human_review": False,
            "Auditor Note": "No overrides or human adjudication used"
        }
    }

    # Sign
    _say(reporter, "sign", message="Signing")
    report["signature"] = sign_report(report)
    _say(reporter, "complete", message="Done", report_id=report["report_id"])
    return report

if __name__ == "__main__":
    user_text = input("Enter text to evaluate: ")
    result = evaluate_text(user_text)
    print(json.dumps(result, indent=2))