import sys
sys.path.insert(0, '.')
from utils.gibberish_check import token_analysis, is_unanalyzable

text = "jgiuwgf hgfiyey gf fuwgfiugf efywegfiywe vbfiuw efiuu wgfui eui fow effiywgfougweofuug weofug eouf gfouwef yousegu we"

result = token_analysis(text)
print("token_count   :", result["token_count"])
print("evaluated     :", result["evaluated"])
print("passed        :", result["passed"])
print("pass_fraction :", result["pass_fraction"])
print("is_unanalyzable:", result["is_unanalyzable"])
print()
print("Per-token breakdown:")
for d in result["token_details"]:
    st = d.get("status", "")
    if st in ("skipped_short_or_digit", "skipped_empty"):
        print("  SKIP  " + d["stripped"])
    else:
        token_str = d["stripped"].ljust(30)
        vr = d.get("vowel_ratio", 0)
        mc = d.get("max_consonant_run", 0)
        al = d.get("alpha_len", 0)
        p  = "PASS" if d["passes"] else "FAIL"
        print(f"  {p}  {token_str}  vowel_ratio={vr}  max_cons={mc}  alpha_len={al}")
