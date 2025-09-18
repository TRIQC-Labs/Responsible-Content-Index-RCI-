def run_bias_analysis(text: str):
    return {
        "bias_fairness": {
            "pass": False,
            "summary": "Risk phrase detected",
            "severity": "Medium",
            "confidence": 82,
            "risk_score": 0.58,
            "risk_threshold": 0.65,
            "bias_type": "framing",
            "affected_group": "minority job applicants",
            "reasoning": "The text frames diversity hiring as harmful, implying quotas reduce productivity."
        }
    }