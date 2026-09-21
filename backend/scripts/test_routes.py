"""Test des routes Flask (sans server.js)."""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.getenv("APP_URL", "http://127.0.0.1:5000").rstrip("/")


def get(path, follow=False):
    req = urllib.request.Request(f"{BASE}{path}")
    if not follow:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        try:
            r = opener.open(req, timeout=10)
            return r.status, r.geturl()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Location", "")
    r = urllib.request.urlopen(req, timeout=10)
    return r.status, r.geturl()


def post_json(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


print(f"=== Routes Flask @ {BASE} ===\n")

pages = [
    ("/", 200),
    ("/login", 200),
    ("/register", 200),
    ("/stagiaire", 302),
    ("/rh", 302),
    ("/affectation", 302),
]

for path, expected in pages:
    code, loc = get(path)
    ok = code == expected
    print(f"  [{'OK' if ok else 'FAIL'}] GET {path} -> {code}" + (f" -> {loc}" if loc else ""))

print("\n=== API /api/apply (insertion test) ===")
code, body = post_json(
    "/api/apply",
    {
        "first_name": "Test",
        "last_name": "Flask",
        "phone": "0600000000",
        "school": "EMI",
        "specialty": "Info",
        "zone": "Siège Social - Casablanca",
        "start": "2026-06-01",
        "end": "2026-08-31",
    },
)
ok = code == 200 and body.get("success")
print(f"  [{'OK' if ok else 'FAIL'}] POST /api/apply -> {code} {body}")

print("\n=== Upload PDF (fichier test) ===")
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
test_pdf = os.path.join(project_root, "frontend", "static", "test_doc.pdf")
if os.path.isfile(test_pdf):
    import mimetypes
    from email.mime.multipart import MIMEMultipart

    try:
        import requests

        with open(test_pdf, "rb") as f:
            r = requests.post(
                f"{BASE}/api/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"type": "cv", "candidate_id": "test_flask"},
                timeout=15,
            )
        ok = r.status_code == 200 and r.json().get("success")
        print(f"  [{'OK' if ok else 'FAIL'}] POST /api/upload -> {r.status_code} {r.text[:120]}")
    except ImportError:
        print("  [SKIP] requests non installé pour test upload")
else:
    print("  [SKIP] frontend/static/test_doc.pdf absent")

sys.exit(0)
