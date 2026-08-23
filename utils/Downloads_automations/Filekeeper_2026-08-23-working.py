# ═══════════════════════════════════════════════════════════════════════════════
#  filekeeper.net extractor — NO browser, NO captcha solver.
#  filekeeper is a standard XFileSharing site: the download page runs a countdown
#  then POSTs `op=download2` back to the file URL; the CDN link (dlproxy.uk) comes
#  back in the 302 Location header. We just replicate that POST with curl_cffi.
#  Accepts filekeeper.net links directly, or a paste.fitgirl link that decrypts
#  to filekeeper links. Self-contained: run this cell alone, no other cell needed.
#
#  WHERE IT RUNS:
#    * Google Colab            -> works (the `%pip` line is a Jupyter magic).
#    * Local Jupyter notebook  -> works (same magic support).
#    * Local plain script (python file.py) -> the `%pip install` line below is a
#      Jupyter magic, NOT valid Python, so it raises SyntaxError. To run as a
#      plain script, delete that line and instead `pip install curl_cffi cryptography`
#      once in your terminal.
# ═══════════════════════════════════════════════════════════════════════════════
%pip install -q curl_cffi cryptography

import re
import json
import zlib
import time
import base64
from curl_cffi import requests as cffi_requests
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── PrivateBin decrypt (paste.fitgirl links) — no browser ─────────────────────
_BASE58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _base58_decode(s):
    num = 0
    for ch in s:
        num = num * 58 + _BASE58.index(ch)
    result = b''
    while num > 0:
        num, rem = divmod(num, 256)
        result = bytes([rem]) + result
    return b'\x00' * (len(s) - len(s.lstrip('1'))) + result


def decrypt_privatebin(url, password=''):
    """Decrypt a PrivateBin v2 paste. The key lives in the URL fragment."""
    paste_url, url_key = url.split('#', 1)
    paste_id = paste_url.split('?')[-1]
    base_url = paste_url[:paste_url.index('?')]

    res = cffi_requests.get(f"{base_url}?{paste_id}",
                            headers={"Accept": "application/json"},
                            impersonate="chrome", timeout=60)
    data = res.json()
    if data.get('status') != 0:
        raise ValueError(f"PrivateBin API error: {data}")

    adata = data['adata']
    iv_b64, salt_b64, iterations, key_size, _tag, _algo, _mode, compression = adata[0]
    iv = base64.b64decode(iv_b64)
    salt = base64.b64decode(salt_b64)
    ct = base64.b64decode(data['ct'])

    key_input = _base58_decode(url_key)
    if password:
        key_input += password.encode()

    derived = PBKDF2HMAC(hashes.SHA256(), key_size // 8, salt, iterations).derive(key_input)
    aad = json.dumps(adata, separators=(',', ':')).encode()
    raw = AESGCM(derived).decrypt(iv, ct, aad)
    if compression == 'zlib':
        raw = zlib.decompress(raw, wbits=-15)
    payload = json.loads(raw.decode())
    return payload.get('paste', raw.decode())


def extract_filekeeper_link(url, session=None, wait_countdown=True):
    """Return the direct CDN link for one filekeeper.net file page (or None)."""
    url = url.split('#')[0].strip()
    s = session or cffi_requests.Session(impersonate="chrome")

    page = s.get(url, timeout=60)
    if page.status_code != 200:
        print(f"  GET {page.status_code} for {url}")
        return None

    def _attr(name, default=""):
        m = re.search(rf'data-{name}="([^"]*)"', page.text)
        return m.group(1) if m else default

    code = _attr("code") or url.rstrip('/').split('/')[-1]
    if _attr("has-captcha") == "true":
        print(f"  {code}: page requires a captcha — needs the browser flow, skipping.")
        return None

    if wait_countdown:
        try:
            time.sleep(int(_attr("countdown", "5")) + 1)
        except ValueError:
            time.sleep(6)

    data = {
        "op": "download2",
        "id": code,
        "rand": _attr("rand"),
        "referer": _attr("referer"),
        "method_free": _attr("method") or "Free download",
        "down_direct": "1",
    }
    resp = s.post(url, data=data, timeout=60, allow_redirects=False)
    link = resp.headers.get("location")
    if not link:
        m = re.search(r'https://[^\s"\'<>]+dlproxy[^\s"\'<>]+', resp.text)
        link = m.group(0) if m else None
    if not link:
        print(f"  {code}: no CDN link (status={resp.status_code}).")
    return link


def extract_filekeeper_links(link_inputs):
    """Process a multi-line block of filekeeper.net and/or paste.fitgirl links."""
    lines = [x.strip() for x in link_inputs.splitlines()
             if x.strip() and not x.strip().startswith('#')]

    results = []
    session = cffi_requests.Session(impersonate="chrome")
    for line in lines:
        if line.startswith("https://paste.fitgirl"):
            try:
                markdown = decrypt_privatebin(line)
                targets = re.findall(r'https://filekeeper\.net/\S+', markdown)
            except Exception as e:
                print(f"  Error decrypting {line}: {e}. Skipping.")
                continue
        elif "filekeeper.net" in line:
            targets = [line]
        else:
            print(f"  Unsupported link: {line}")
            continue

        for t in targets:
            link = extract_filekeeper_link(t, session=session)
            if link:
                print(f"  \u2713 {link}")
                results.append(link)
    return results


FILEKEEPER_INPUTS = '''
# One link per line. Lines starting with # are ignored.
# Paste filekeeper.net links or a paste.fitgirl-repacks.site link.

https://paste.fitgirl-repacks.site/?9b83a394a1d920a1#HNJUSConLNWoHU8vdkuAaHPzjQuAe8C3tShNzbWNTCT9
'''

_fk_links = extract_filekeeper_links(FILEKEEPER_INPUTS)
print(f"\n================ RESULTS ({len(_fk_links)}) ================")
for _i, _l in enumerate(_fk_links, 1):
    print(f"{_i:>2}. {_l}")

if _fk_links:
    with open("filekeeper_links.txt", "w", encoding="utf-8") as _f:
        _f.write("\n".join(_fk_links))
    print(f"\nSaved {len(_fk_links)} link(s) to filekeeper_links.txt")
