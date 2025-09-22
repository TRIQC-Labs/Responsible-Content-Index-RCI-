# controller.py
from __future__ import annotations
import json, hashlib, secrets
import time
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
    if key in result and isinstance(result[key], dict):
        return result[key]
    return result

# --- Normalizers (unchanged) ---
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

    groups = ex.get("affected_groups")
    if isinstance(groups, list):
        seen = []
        for g in groups:
            if isinstance(g, str) and g not in seen:
                seen.append(g)
        groups = seen[:3]
    else:
        groups = None

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
    return {"alg": "ed25519", "sig": "7c1c…e0b9"}

# --- Public API (unchanged evaluate_text) ---
def evaluate_text(text: str, reporter: Optional[Reporter] = None) -> Dict[str, Any]:
    _say(reporter, "start", message="Beginning evaluation", chars=len(text))

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
    bf = normalize_bias_fairness(bias_raw, DEFAULT_THRESHOLDS["bias_fairness"])
    el = normalize_exclusionary(exclusionary_raw, DEFAULT_THRESHOLDS["exclusionary_language"])
    mi = normalize_misinformation(misinformation_raw, DEFAULT_THRESHOLDS["misinformation_risk"])

    _say(reporter, "assemble", message="Assembling certificate")
    report = {
        "report_id": short_id("rep"),
        "created_at": now_iso_pst(),
        "policy_version": POLICY_VERSION,
        "input_sha256": sha256_hex(text),
        "models": {
            "bias_fairness": MODEL_VERSIONS["bias_fairness"],
            "exclusionary_language": MODEL_VERSIONS["exclusionary_language"],
            "misinformation": MODEL_VERSIONS["misinformation"],
        },
        "signature": {"alg": "ed25519", "sig": "7c1c…e0b9"},
        "checks": {
            "bias_fairness": bf,
            "exclusionary_language": el,
            "misinformation_risk": mi
        },
        "audit": {
            "prompt_hash": None,
            "run_id": f"run_{datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')}_{secrets.token_hex(2)}",
            "deterministic_seed": 1337,
            "human_review": False,
            "Auditor Note": "No overrides or human adjudication used"
        }
    }

    _say(reporter, "sign", message="Signing")
    report["signature"] = sign_report(report)
    _say(reporter, "complete", message="Done", report_id=report["report_id"])
    return report

# --- Streaming version for UI ---
def evaluate_text_stream(text: str):
    try:
        yield {"event": "start", "message": "Beginning evaluation", "chars": len(text)}

        yield {"event": "lens_start", "lens": "bias_fairness", "message": "🔍 Checking for hidden bias…"}
        bias_raw = run_bias_analysis(text)
        time.sleep(2) 
        yield {"event": "lens_done", "lens": "bias_fairness"}

        yield {"event": "lens_start", "lens": "exclusionary_language", "message": "🧭 Scanning exclusionary language…"}
        exclusionary_raw = run_exclusionary_analysis(text)
        time.sleep(2) 
        yield {"event": "lens_done", "lens": "exclusionary_language"}

        yield {"event": "lens_start", "lens": "misinformation_risk", "message": "🔎 Assessing factual risk…"}
        misinformation_raw = run_misinformation_analysis(text)
        time.sleep(2) 
        yield {"event": "lens_done", "lens": "misinformation_risk"}

        yield {"event": "normalize", "message": "Putting together results nicely"}
        bf = normalize_bias_fairness(bias_raw, DEFAULT_THRESHOLDS["bias_fairness"])
        el = normalize_exclusionary(exclusionary_raw, DEFAULT_THRESHOLDS["exclusionary_language"])
        mi = normalize_misinformation(misinformation_raw, DEFAULT_THRESHOLDS["misinformation_risk"])

        yield {"event": "assemble", "message": "Assembling certificate"}
        report = {
            "report_id": short_id("rep"),
            "created_at": now_iso_pst(),
            "policy_version": POLICY_VERSION,
            "input_sha256": sha256_hex(text),
            "models": MODEL_VERSIONS,
            "signature": {"alg": "ed25519", "sig": "7c1c…e0b9"},
            "checks": {
                "bias_fairness": bf,
                "exclusionary_language": el,
                "misinformation_risk": mi
            },
            "audit": {
                "prompt_hash": None,
                "run_id": f"run_{datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')}_{secrets.token_hex(2)}",
                "deterministic_seed": 1337,
                "human_review": False,
                "Auditor Note": "No overrides or human adjudication used"
            }
        }

        time.sleep(2) 
        yield {"event": "sign", "message": "Signing"}
        report["signature"] = sign_report(report)

        yield {"event": "report_end", "report": report}
    except Exception as e:
        yield {"event": "error", "message": str(e)}
    finally:
        yield {"event": "complete"}


def test_evaluate_text_stream(text: str):

    # Fake "streaming" events
    yield {"event": "start", "message": "Beginning evaluation", "chars": len(text)}

    yield {"event": "lens_start", "lens": "bias_fairness", "message": "🔍 Checking for hidden bias…"}
    yield {"event": "lens_done", "lens": "bias_fairness"}

    yield {"event": "lens_start", "lens": "exclusionary_language", "message": "🧭 Scanning exclusionary language…"}
    yield {"event": "lens_done", "lens": "exclusionary_language"}

    yield {"event": "lens_start", "lens": "misinformation_risk", "message": "🔎 Assessing factual risk…"}
    yield {"event": "lens_done", "lens": "misinformation_risk"}

    yield {"event": "normalize", "message": "Putting together results nicely"}

    yield {"event": "assemble", "message": "Assembling certificate"}
    report = {
        "report_id": "rep_test1234",
        "created_at": "2025-09-21T16:05:00-07:00",
        "policy_version": "v1.0.0",
        "input_sha256": "abcd1234ef567890deadbeefcafef00d1234567890abcdef1234567890abcdef",
        "models": {
            "origin": "origin_v1.2",
            "bias_fairness": "bias_v2.1",
            "exclusionary_language": "exclusion_v3.0",
            "misinformation_risk": "misinfo_v0.9"
        },
        "signature": {"alg": "ed25519", "sig": "deadbeefcafebabe12345678"},
        "checks": {
            "bias_fairness": {
                "bias_detected": False,
                "confidence": 0.12,
                "reasoning": "No significant stereotyping or group targeting detected."
            },
            "exclusionary_language": {
                "exclusion_detected": False,
                "confidence": 0.08,
                "reasoning": "Language is inclusive and neutral."
            },
            "misinformation_risk": {
                "risk_detected": False,
                "confidence": 0.10,
                "reasoning": "No factual claims found that could be misleading."
            }
        },
        "audit": {
            "prompt_hash": "hash_test_123",
            "run_id": "run_2025-09-21T23:05Z_ab12",
            "deterministic_seed": 1337,
            "human_review": False,
            "Auditor Note": "This is a test run. No overrides or adjudication applied."
        }
    }

    yield {"event": "sign", "message": "Signing"}
    yield {"event": "report_end", "report": report}
    yield {"event": "complete"}