%pip install -q curl_cffi cryptography

import re
import json
import zlib
import base64
import time
from curl_cffi import requests as cffi_requests
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
    """Decrypt a PrivateBin v2 paste without a browser.
    The decryption key lives in the URL fragment and never touches the server.
    """
    paste_url, url_key = url.split('#', 1)
    paste_id = paste_url.split('?')[-1]
    base_url  = paste_url[:paste_url.index('?')]

    res  = cffi_requests.get(f"{base_url}?{paste_id}",
                             headers={"Accept": "application/json"},
                             impersonate="chrome",
                             timeout=60)
    data = res.json()
    if data.get('status') != 0:
        raise ValueError(f"PrivateBin API error: {data}")

    adata = data['adata']
    iv_b64, salt_b64, iterations, key_size, _tag_size, _algo, _mode, compression = adata[0]

    iv   = base64.b64decode(iv_b64)
    salt = base64.b64decode(salt_b64)
    ct   = base64.b64decode(data['ct'])

    key_input = _base58_decode(url_key)
    if password:
        key_input += password.encode()

    derived = PBKDF2HMAC(hashes.SHA256(), key_size // 8, salt, iterations).derive(key_input)
    aad     = json.dumps(adata, separators=(',', ':')).encode()

    raw = AESGCM(derived).decrypt(iv, ct, aad)

    if compression == 'zlib':
        raw = zlib.decompress(raw, wbits=-15)   # raw deflate

    # The paste payload is {"paste": "...markdown..."}
    payload = json.loads(raw.decode())
    return payload.get('paste', raw.decode())
# ─────────────────────────────────────────────────────────────────────────────

def extract_download_links_from_pages(urls, max_retries=3):
    # fuckingfast.co now uses HTMX: the download button POSTs to /f/{id}/go
    # and the actual CDN download URL is returned in the `hx-redirect` response header.
    extracted_links = []
    failed_urls = list(urls)

    for attempt in range(max_retries):
        if not failed_urls:
            break
        if attempt > 0:
            print(f"\n--- Retry attempt {attempt}/{max_retries-1} for {len(failed_urls)} failed URLs ---")
            time.sleep(3)

        still_failing = []
        for url in failed_urls:
            try:
                # Strip the hash fragment and extract the file ID from the path
                file_id = url.split('#')[0].rstrip('/').split('/')[-1]
                page_url = f"https://fuckingfast.co/{file_id}"

                htmx_headers = {
                    "Referer": page_url,
                    "HX-Request": "true",
                    "HX-Current-URL": page_url,
                    "HX-Target": "null",
                }

                response = cffi_requests.post(
                    f"https://fuckingfast.co/f/{file_id}/go",
                    headers=htmx_headers,
                    impersonate="chrome"
                )

                download_link = response.headers.get("hx-redirect")

                if download_link:
                    extracted_links.append(download_link)
                else:
                    print(f"  No hx-redirect for {url} | status={response.status_code} | body={response.text[:120]}")
                    still_failing.append(url)

            except Exception as e:
                print(f"  Error for {url}: {type(e).__name__}: {e}")
                still_failing.append(url)

        failed_urls = still_failing

    if failed_urls:
        print(f"\n\n{'='*50}")
        print(f"FAILED after {max_retries} attempts ({len(failed_urls)} URLs):")
        print('='*50)
        for url in failed_urls:
            print(url)

    return extracted_links

link_inputs = '''
# TODOWN

# https://fitgirl-repacks.site/assassins-creed-black-flag-resynced/
# Assassin’s Creed: Black Flag Resynced – Deluxe Edition, v1.0.6 + 10 DLCs/Bonuses
https://paste.fitgirl-repacks.site/?b7f1f779cba7bfbc#GupC3qoJmtxSCbKUriCn5WoMMhVbExvAzLS4Y4Y5M79U




# https://fuckingfast.co/i2f26tc5q47l#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part01.rar
# https://fuckingfast.co/hr6ojn4wrv7i#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part02.rar
# https://fuckingfast.co/ypsl9c56b8dr#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part03.rar
# https://fuckingfast.co/0gw5ccbjr3cj#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part04.rar
# https://fuckingfast.co/x96353167o4y#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part05.rar
# https://fuckingfast.co/rfynvbyay46p#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part06.rar
# https://fuckingfast.co/w6sz5it03hfs#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part07.rar
# https://fuckingfast.co/d0xgkahg22lj#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part08.rar
# https://fuckingfast.co/jhfnyu4cd2lb#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part09.rar
# https://fuckingfast.co/1nt3g2sf2s1x#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part10.rar
# https://fuckingfast.co/uyqf3yfp6nu6#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part11.rar
# https://fuckingfast.co/f2yein0af0x3#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part12.rar
# https://fuckingfast.co/xqsj71kdbvtr#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part13.rar
# https://fuckingfast.co/2zwbjduiwvsj#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part14.rar
# https://fuckingfast.co/htnbcown9n1a#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part15.rar
# https://fuckingfast.co/bjb54t7zcvgf#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part16.rar
# https://fuckingfast.co/yuvwbyd65btw#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part17.rar
# https://fuckingfast.co/h37yz8leosux#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part18.rar
# https://fuckingfast.co/f4hjeq66ml2b#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part19.rar
# https://fuckingfast.co/z2k7xnbqss80#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part20.rar
# https://fuckingfast.co/f4re4egkwjv9#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part21.rar
# https://fuckingfast.co/7xft39n78qo7#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part22.rar
# https://fuckingfast.co/js9ywdkqjklk#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part23.rar
# https://fuckingfast.co/48tee3rb30e6#The_Talos_Principle_Reawakened_--_fitgirl-repacks.site_--_.part24.rar

# https://fuckingfast.co/t53azsl6j81y#The.Talos.Principle.Reawakened.Update.v1.01b-RUNE.rar

# https://fuckingfast.co/u5h1dbxkcwqr#fg-optional-videos.part01.rar
# https://fuckingfast.co/ldhutgkee2nq#fg-optional-videos.part02.rar
# https://fuckingfast.co/h8q3jxitony0#fg-optional-videos.part03.rar
# https://fuckingfast.co/v9h70g18omp8#fg-optional-videos.part04.rar
# https://fuckingfast.co/utub5e4mvetl#fg-optional-videos.part05.rar
# https://fuckingfast.co/ob50bevleofd#fg-optional-videos.part06.rar
# https://fuckingfast.co/g9ll6fmfu2uk#fg-optional-videos.part07.rar
# https://fuckingfast.co/z1535p8dsxfk#fg-optional-videos.part08.rar
# https://fuckingfast.co/7i5l1xxjbr47#fg-optional-videos.part09.rar
# https://fuckingfast.co/9samp27y7sv3#fg-optional-videos.part10.rar
# https://fuckingfast.co/fnxxwl4ut97a#fg-optional-videos.part11.rar
# https://fuckingfast.co/qa5b1n7prmot#fg-optional-videos.part12.rar
# https://fuckingfast.co/kpcrvuizodpe#fg-optional-videos.part13.rar








# https://fitgirl-repacks.site/escape-simulator-2/
# Escape Simulator 2 – v16494r + Bonus OST + Online Co-op
# https://paste.fitgirl-repacks.site/?7cccc488979584a1#3Wf4HjWYNynRbPr3pRiJK6KdmngWoE5GsV45roGkctma

# https://fuckingfast.co/qh0zlqvwd6p5#Escape.Simulator.2.Update.v20448r-RUNE.part4.rar
# https://fuckingfast.co/abbq99wkjv70#Escape.Simulator.2.Update.v20448r-RUNE.part3.rar
# https://fuckingfast.co/rio1wdccl83k#Escape.Simulator.2.Update.v20448r-RUNE.part2.rar
# https://fuckingfast.co/j2fpdr7274as#Escape.Simulator.2.Update.v20448r-RUNE.part1.rar
# https://fuckingfast.co/i9umifidu89j#Escape.Simulator.2.Update.v18159r-RUNE.rar
# https://fuckingfast.co/ymlauzpwdfch#Escape.Simulator.2.Update.v18158r-RUNE.part3.rar
# https://fuckingfast.co/x95vq0jk48x7#Escape.Simulator.2.Update.v18158r-RUNE.part2.rar
# https://fuckingfast.co/5747nqh6abej#Escape.Simulator.2.Update.v18158r-RUNE.part1.rar

# https://fuckingfast.co/p08epchlftdu#STALKER_2_Heart_of_Chornobyl_Update_from_v1.8.1_to_v1.9.0-ElAmigos.part3.rar
# https://fuckingfast.co/22wwmrpz5h24#STALKER_2_Heart_of_Chornobyl_Update_from_v1.8.1_to_v1.9.0-ElAmigos.part2.rar
# https://fuckingfast.co/juim3a8tf1lu#STALKER_2_Heart_of_Chornobyl_Update_from_v1.8.1_to_v1.9.0-ElAmigos.part1.rar
# https://fuckingfast.co/3j0b0qv12va9#S.T.A.L.K.E.R.2.Heart.of.Chornobyl.Update.v1.8.1-RUNE.part3.rar
# https://fuckingfast.co/bctz22weer4m#S.T.A.L.K.E.R.2.Heart.of.Chornobyl.Update.v1.8.1-RUNE.part2.rar
# https://fuckingfast.co/149xc53iukcb#S.T.A.L.K.E.R.2.Heart.of.Chornobyl.Update.v1.8.1-RUNE.part1.rar
# https://fuckingfast.co/w07njcxws0sn#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part10.rar
# https://fuckingfast.co/t7cpn73zjwoq#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part09.rar
# https://fuckingfast.co/8hdwuprtdwmr#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part08.rar
# https://fuckingfast.co/evy3hpj7xj1e#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part07.rar
# https://fuckingfast.co/9v5806qr11ms#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part06.rar
# https://fuckingfast.co/2rvo2yq9lhf5#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part05.rar
# https://fuckingfast.co/li7v0gj8bsmt#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part04.rar
# https://fuckingfast.co/y3zjo9ma9tv6#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part03.rar
# https://fuckingfast.co/cpr31q1b61hx#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part02.rar
# https://fuckingfast.co/o9yrxn1mr841#STALKER_2_Heart_of_Chornobyl_Update_from_v1.6.1_to_v1.7.0-ElAmigos.part01.rar





# Marvel’s Spider-Man 2: Digital Deluxe Edition, v1.130.1.0/v1.131.0.0 + 2 DLCs + Unlocker + Bonus Soundtrack

# https://fitgirl-repacks.site/marvels-spider-man-2/
# https://paste.fitgirl-repacks.site/?aa7ee62c43546e4f#HdgTUYUKFGRt2uVMyfx4i2KaZ8eS31oLoUJwzMaZqKJ7
# https://fuckingfast.co/l2fk9bbr2kyu#Marvels_SpiderMan_2_Update_from_v1.526_to_v2.629-ElAmigos.rar
# https://fuckingfast.co/jehskk36zfs5#Marvels.Spider-Man.2.Update.v1.526.0.0-RUNE.rar
# https://fuckingfast.co/j5udcsk6284z#Marvels.Spider-Man.2.Update.v1.318.1.0-RUNE.part2.rar
# https://fuckingfast.co/ojpf10i53kno#Marvels.Spider-Man.2.Update.v1.318.1.0-RUNE.part1.rar


# Palworld – v1.0.0.100427 (Release) + Bonus OST
# https://fitgirl-repacks.site/palworld/
# https://paste.fitgirl-repacks.site/?7eae4d3ee5df85dc#8kAMZ5rfPhxkb47vbUDY49zHuk4b6BNmfK7fVH1qfoDG
# https://fuckingfast.co/3k4omhw8o0xj#Palworld.Build.24088745.Steamworks.Fix-SOVEREIGN.rar

# The Last Gas Station – v1.0.0.304 + Bonus OST
# https://fuckingfast.co/5xiomf6lm7kh#The_Last_Gas_Station_--_fitgirl-repacks.site_--_.rar

# Dying Light: The Beast Restored Land – Definitive Edition, v1.6.0 + 11 DLCs/Bonuses + Multiplayer
# https://fitgirl-repacks.site/dying-light-the-beast/
# https://paste.fitgirl-repacks.site/?086392109b40ecd4#AWqomRjN17h25ATe6hqetLGQqUEDeLTdz9kCNjAKbjeG
# https://fuckingfast.co/e77sfvg834ad#Dying_Light_The_Beast_Update_from_v1.6.0_to_v1.6.2-ElAmigos.rar
# https://fuckingfast.co/5dfvkreznao6#Dying_Light_The_Beast_Update_from_v1.6.2_to_v1.6.3-ElAmigos.rar


'''


links = [x.strip() for x in link_inputs.splitlines() if x.strip() and not x.strip().startswith('#')]

for link_input in links:
  urls_to_process = []

  if link_input.startswith('https://paste.fitgirl'):
    try:
      markdown = decrypt_privatebin(link_input)
      urls_to_process = re.findall(r'https://fuckingfast\.co/\S+', markdown)
    except cffi_requests.errors.Timeout as e:
      print(f"  Timeout error while decrypting PrivateBin link {link_input}: {e}. Skipping.")
      continue
    except Exception as e:
      print(f"  Error decrypting PrivateBin link {link_input}: {e}. Skipping.")
      continue

  elif link_input.startswith('https://fuckingfast.co'):
    urls_to_process = link_input.split(' ')
    # print('fuckingfast')
  else:
    print("Unsupported link type. Please provide a paste.fitgirl or fuckingfast.co link.")

  if urls_to_process:
      all_download_links = extract_download_links_from_pages(urls_to_process)

      if all_download_links:
          # print("\nAll Extracted Download Links:")
          for download_link in all_download_links:
              print(download_link+'\n')
              # print('\n')
      else:
          print("\nNo download links were extracted from the provided URLs.")
  else:
      print("\nNo URLs to process.")