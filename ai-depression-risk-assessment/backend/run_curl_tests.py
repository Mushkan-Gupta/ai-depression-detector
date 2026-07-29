import subprocess
import os

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc4NTIxODQ0MSwianRpIjoiZTFlOTMwYmQtZTkyMi00NTZkLWE0YTgtMWI2OGRhYzRjNDRlIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjZhNjg0NTg5YjkzNDI0NGUxOTdjYzViZCIsIm5iZiI6MTc4NTIxODQ0MSwiY3NyZiI6IjU4NjE1YTM4LTFkNDMtNDVlNy1iY2E3LTZlYjM1ZTliM2I3YyIsImV4cCI6MTc4NTgyMzI0MSwiZW1haWwiOiJjb25zZW50X3ZlcmlmaWVyX3VzZXI5OUBleGFtcGxlLmNvbSIsIm5hbWUiOiJDb25zZW50IFRlc3QgVXNlciJ9.fqaOhNZ9HzvrG9YimVn7hwLaBbqDpW81_ZNORF5BkM8"

tests = [
    ("a) POST /peer/consent, first-time consent", [
        "curl.exe", "-i", "-X", "POST", "http://127.0.0.1:5000/peer/consent",
        "-H", f"Authorization: Bearer {token}"
    ]),
    ("b) POST /peer/consent, second time (re-affirm)", [
        "curl.exe", "-i", "-X", "POST", "http://127.0.0.1:5000/peer/consent",
        "-H", f"Authorization: Bearer {token}"
    ]),
    ("c) POST /peer/consent, no auth token", [
        "curl.exe", "-i", "-X", "POST", "http://127.0.0.1:5000/peer/consent"
    ]),
    ("d) GET /peer/_test-consent-gate (now-removed dummy route)", [
        "curl.exe", "-i", "-X", "GET", "http://127.0.0.1:5000/peer/_test-consent-gate",
        "-H", f"Authorization: Bearer {token}"
    ])
]

for title, cmd in tests:
    print(f"=== {title} ===")
    display_cmd = []
    for arg in cmd:
        if token in arg:
            display_cmd.append(arg.replace(token, "<REDACTED>"))
        else:
            display_cmd.append(arg)
    print("Command:", " ".join(display_cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.replace(token, "<REDACTED>")
    err = res.stderr.replace(token, "<REDACTED>")
    print(out)
    if err:
        print("STDERR:", err)
    print("\n" + "-"*60 + "\n")
