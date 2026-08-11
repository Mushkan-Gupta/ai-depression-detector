"""
Probe: Run TP-2 through the FULL /predict pipeline via Flask test client.
This includes real ML model scoring + blending + route (b) context-gate check.
Run with: venv\Scripts\python.exe -m pytest tests/probe_tp2_predict.py -v -s
"""
import pytest


TP2_TEXT = "Everything I try feels pointless, I don't see why I bother anymore."


def test_tp2_full_predict_pipeline(client):
    """
    Run TP-2 through the complete /predict pipeline.
    Reports ml_dep_prob and final blended risk.
    Does NOT assert a specific outcome — just reports facts.
    """
    resp = client.post("/predict", json={"journal": TP2_TEXT})
    assert resp.status_code == 200, f"Unexpected HTTP status: {resp.status_code}"
    data = resp.get_json()

    risk       = data.get("risk")
    confidence = data.get("confidence")
    ml_prob    = data.get("ml_dep_prob", "(not exposed in response)")

    print()
    print("=" * 65)
    print("TP-2: FULL /predict pipeline result (keyword + ML blend)")
    print("=" * 65)
    print(f"  Text       : {TP2_TEXT}")
    print(f"  risk       : {risk}")
    print(f"  confidence : {confidence}")
    print(f"  ml_dep_prob: {ml_prob}")
    print(f"  Full JSON  : {data}")
    print()

    if risk in ("Moderate", "High"):
        print("  VERDICT: Option 1 CONFIRMED — ML route (b) rescued TP-2.")
        print("  ml_dep_prob >= 0.4 triggered the gated indirect ideation floor.")
    else:
        print("  VERDICT: Option 1 does NOT rescue TP-2.")
        print("  ml_dep_prob < 0.4 — all three context-gate routes failed.")
        print("  This is a documented residual gap in the keyword/ML layer.")
    print("=" * 65)
    print()

    # Always pass — this is a reporting test, not an assertion test
    assert True
