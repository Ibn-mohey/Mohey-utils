"""
fuckingfast.co link extractor — LOCAL (Windows/desktop) version.

Why local: fuckingfast.co guards the download with Cloudflare Turnstile, which
hard-fails on datacenter IPs (Colab). On a normal home IP it passes SILENTLY, so
a real headful browser gets a token automatically — no captcha solver needed.

One-time setup (run in a terminal):
    pip install playwright curl_cffi cryptography
    playwright install chromium

Then just run:
    python fuckingfast_local.py

Put your links in LINK_INPUTS below. Supports:
  * https://fuckingfast.co/<id>#name.rar          (direct file pages)
  * https://paste.fitgirl-repacks.site/?...#key    (decrypted, then its ff links)
Results are printed and written to fuckingfast_links.txt.
"""

import re
import json
import zlib
import base64
import asyncio

from curl_cffi import requests as cffi_requests
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.async_api import async_playwright

# ── PrivateBin helpers ────────────────────────────────────────────────────────
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


# ── fuckingfast.co extraction via a real headful browser ──────────────────────
async def _extract_all(urls, headless=False, per_url_timeout=90):
    extracted = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        # accept_downloads=False so following the CDN link never pulls the file.
        ctx = await browser.new_context(accept_downloads=False)

        # fuckingfast opens an ad tab on the first click — close any extra tab.
        async def _close_popup(pg):
            try:
                await pg.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass
            if pg is not page:
                try:
                    await pg.close()
                except Exception:
                    pass
        ctx.on("page", lambda pg: asyncio.create_task(_close_popup(pg)))

        page = await ctx.new_page()

        for url in urls:
            fid = url.split('#')[0].rstrip('/').split('/')[-1]
            got = {}

            async def on_resp(r, fid=fid, got=got):
                if r.request.method == "POST" and r.url.rstrip('/').endswith(f"/f/{fid}/go"):
                    loc = await r.header_value("hx-redirect")
                    if loc:
                        got["link"] = loc

            page.on("response", on_resp)
            try:
                await page.goto(f"https://fuckingfast.co/{fid}",
                                wait_until="domcontentloaded",
                                timeout=per_url_timeout * 1000)
                # wait for Turnstile to silently issue a token
                try:
                    await page.wait_for_function(
                        "() => !!window.turnstileToken || !!window.dlCleared",
                        timeout=per_url_timeout * 1000)
                except Exception:
                    pass

                btn = page.locator("a[hx-post]")
                for _ in range(3):
                    if "link" in got:
                        break
                    try:
                        await btn.click(timeout=5000, no_wait_after=True)
                    except Exception:
                        pass
                    for _ in range(20):
                        if "link" in got:
                            break
                        await asyncio.sleep(0.5)
            except Exception as e:
                print(f"  Error for {fid}: {type(e).__name__}: {e}")
            finally:
                page.remove_listener("response", on_resp)

            if "link" in got:
                print(f"  \u2713 {got['link']}")
                extracted.append(got["link"])
            else:
                print(f"  \u2717 no link for {fid} (Turnstile not cleared)")

        await ctx.close()
        await browser.close()
    return extracted


def extract_download_links_from_pages(urls, headless=False):
    return asyncio.run(_extract_all(urls, headless=headless))


# ── your links ────────────────────────────────────────────────────────────────
LINK_INPUTS = '''
# One link per line. Lines starting with # are ignored.
# Paste fuckingfast.co links or a paste.fitgirl-repacks.site link.

https://fuckingfast.co/i2f26tc5q47l#The_Talos_Principle_Reawakened_--_.part01.rar
'''


def main():
    links = [x.strip() for x in LINK_INPUTS.splitlines()
             if x.strip() and not x.strip().startswith('#')]

    all_results = []
    for link_input in links:
        if link_input.startswith('https://paste.fitgirl'):
            try:
                markdown = decrypt_privatebin(link_input)
                urls = re.findall(r'https://fuckingfast\.co/\S+', markdown)
            except Exception as e:
                print(f"  Error decrypting {link_input}: {e}. Skipping.")
                continue
        elif link_input.startswith('https://fuckingfast.co'):
            urls = [link_input]
        else:
            print(f"  Unsupported link: {link_input}")
            continue

        if urls:
            print(f"\nProcessing {len(urls)} url(s)...")
            all_results.extend(extract_download_links_from_pages(urls))

    print("\n================ RESULTS ================")
    for r in all_results:
        print(r)

    if all_results:
        with open("fuckingfast_links.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(all_results))
        print(f"\nSaved {len(all_results)} link(s) to fuckingfast_links.txt")


if __name__ == "__main__":
    main()
