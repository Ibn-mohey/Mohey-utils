# Downloads automations

Scripts that turn a repack/file-host page into a **direct download link** — for
[FitGirl](https://fitgirl-repacks.site/) mirrors and the Arabic site
[Akwam](https://akwam.it/). Most are self-contained: paste links, run, get direct
URLs you can hand to a download manager (IDM/aria2/`wget`).

## Hosts & how they work

| Host | Guard | Approach | Browser? |
|------|-------|----------|----------|
| **filekeeper.net** | 5s countdown | POST `op=download2` → CDN link in the `hx-redirect`/`Location` header | No |
| **fuckingfast.co** | Cloudflare Turnstile | real Chrome mints `window.turnstileToken`, then click DOWNLOAD → `hx-redirect` | Yes |
| **paste.fitgirl-repacks.site** | client-side crypto | decrypt the PrivateBin paste locally (key is in the `#fragment`) | No |
| **akwam.it** | anti-adblock overlays | Selenium removes overlays and follows to the CDN link | Yes |

## Files

- **`Filekeeper_2026-08-23-working.py`** — filekeeper.net extractor. No browser, no
  captcha solver. Accepts filekeeper links directly or a `paste.fitgirl` link (it
  decrypts the paste, pulls the filekeeper links, and resolves each). Writes
  `filekeeper_links.txt`. Runs in Colab / local Jupyter (the `%pip` line is a
  notebook magic — delete it to run as a plain script).
- **`fuckingfast_local.py`** — fuckingfast.co extractor for Windows/desktop. Drives a
  **persistent real-Chrome profile** so Turnstile clears silently, then reads the
  `hx-redirect` link. (Ephemeral automation browsers get bot-flagged and never get a
  token — the persistent profile is the fix.)
- **`local_test.ipynb`** — notebook version of the fuckingfast local flow (persistent
  Chrome + the Jupyter event-loop/ProactorEventLoop handling).
- **`colab_test.ipynb`** — Colab workbench: fuckingfast via curl/HTMX and a manual
  Turnstile-solve path (Xvfb + VNC + noVNC viewer), plus the filekeeper extractor.
- **`akowam.py`** — Akwam extractor via `google-colab-selenium`; strips anti-adblock
  overlays and collects the final links.
- **`Fucking_fast_2026-08-22-retired.py`**, **`Fucking_fast_2026_07_06-retired.py`**,
  **`old_akwam.PY`** — retired/older versions kept for reference.

## Notes

- Resolved links are often **short-lived / single-use** — grab them right before
  downloading.
- `.ff_profile/` (the persistent Chrome profile) is generated locally and git-ignored.
