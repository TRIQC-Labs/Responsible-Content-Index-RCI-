def run_exclusionary_analysis(text: str):
    return {
        "exclusionary_language": {
            "pass": False,
            "summary": "Risk phrase detected",
            "reasoning": "The phrase suggests exclusion by portraying diverse candidates as lowering standards.",
            "severity": "Medium",
            "confidence": 88,
            "risk_score": 0.52,
            "risk_threshold": 0.65,
            "exclusionary_type": "stereotyping_phrase",
            "affected_groups": ["minority job applicants"],
            "spans": [
                {
                    "text": "Diversity hiring quotas lower workplace productivity",
                    "char_start": 0,
                    "char_end": 53,
                    "policy_code": "EL-001",
                    "suggested_rewrite": "Diversity hiring practices strengthen workplace outcomes when implemented effectively."
                }
            ]
        }
    }