%pip install -q google-colab-selenium webdriver-manager undetected-chromedriver

import google_colab_selenium as gs
import undetected_chromedriver as uc

from IPython.core.display import display, HTML
from datetime import date
from datetime import datetime
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

options = uc.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = uc.Chrome(options=options, headless=True)

import re
import requests
from bs4 import BeautifulSoup
import time

def extract_download_links_from_pages(urls):
    extracted_links = []
    for url in urls:
        try:
            driver.get(url)
            # Wait for Cloudflare challenge to pass
            WebDriverWait(driver, 30).until(
                lambda d: "Just a moment" not in d.title
            )
            time.sleep(2)
            page_source = driver.page_source

            download_link = None
            # Try finding in script tags
            match = re.search(r'function\s+download\s*\(\)\s*\{[^}]*window\.open\("(https?://[^"]+)"\)', page_source, re.DOTALL)
            if match:
                download_link = match.group(1)
            else:
                # Fallback: look for any window.open with a download URL
                match = re.search(r'window\.open\("(https?://[^"]+)"\)', page_source)
                if match:
                    download_link = match.group(1)

            if download_link:
                extracted_links.append(download_link)
            else:
                # Debug: dump page HTML to see what Selenium actually loaded
                print(f"  DEBUG for {url}:")
                print(page_source[:3000])
                print("\n... END DEBUG ...\n")

        except Exception as e:
            print(f"  An error occurred for {url}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    return extracted_links

# link_input = input()
link_inputs = '''
https://fuckingfast.co/1lmvhdj79suj#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part070.rar
https://fuckingfast.co/bjizlospqneh#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part071.rar
https://fuckingfast.co/865oqygy8d7m#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part072.rar
https://fuckingfast.co/kl1airt3f2m2#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part073.rar
https://fuckingfast.co/wxc6wxkuknwh#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part074.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part075.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part079.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part080.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part081.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part082.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part083.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part084.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part085.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part086.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part087.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part088.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part089.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part090.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part091.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part092.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part093.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part094.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part095.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part096.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part097.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part098.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part099.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part100.rar
https://fuckingfast.co/wy2oz7eie1xd#EA_SPORTS_FC_26_--_fitgirl-repacks.site_--_.part101.rar
'''


# FIFA https://paste.fitgirl-repacks.site/?0b90f7ed1fbf4c02#6L6us7S7JhEw5cxk6pX5pZNp9gWPDfmLCBMnsyRbA7aZ

# https://fitgirl-repacks.site/the-witcher-2-assassins-of-kings-enhanced-edition/ 8.7
# https://paste.fitgirl-repacks.site/?289b024f04c36e43#78zvcftZe8hXd6cZRLDDiTU8zxe263gkMfV3gJ3atnSs

# https://paste.fitgirl-repacks.site/?c991b16de05a1388#6H4YubwVmAw3zTEAAMg8xhGmSGEqWr7fHoWqxtYSDYjd
# https://fitgirl-repacks.site/riven/ 14.6

#https://fitgirl-repacks.site/the-talos-principle-reawakened/ 30.3
#https://paste.fitgirl-repacks.site/?3e5529e6d8100256#8DX57hipkUbiL45s8jVNnxgEUqnVwb2N5Adi3tgbW3ZW
#
#https://paste.fitgirl-repacks.site/?fe8dc326b94d7673#DQn61xkU6pwqv5x9vZzJAaskinThDZVSYGvarRHQHpXJ
#https://fitgirl-repacks.site/the-talos-principle-2/ 67.6 GB

#https://fitgirl-repacks.site/cyberpunk-2077/ 55.7
#Cyberpunk 2077: Ultimate Edition – v2.3 + All DLCs + Bonus Content + REDmod
# https://paste.fitgirl-repacks.site/?1af473c3a46fca70#FQgNRR2ga5niMyupqPxeYLGehPk3C4kdLRqybdw46WKG
# Cyberpunk_2077_Update_from_v2.30_to_v2.31-ElAmigos.rar
# https://filecrypt.cc/Container/C05C1202D3.html

# Marvel’s Spider-Man Remastered – v1.812.1.0 + DLC + SSE Fix
# https://fitgirl-repacks.site/marvels-spider-man-remastered/ 37.6
# https://paste.fitgirl-repacks.site/?262c85d934954c96#ENBh23cckBbF1j2LL5TdnqpyS4r39hptyHUEbuEQG5XC
# https://filecrypt.cc/Container/FDD8F2905F.html Marvels_Spider_Man_Remastered_Update_b9304506_to_b12423814_AiO_MULTI23-Christsnatcher.rar
# https://filecrypt.cc/Container/B748894C90.html Marvels_Spider_Man_Remastered_Update_b12423814_to_b14752622_v3.618-CS.rar

# https://fitgirl-repacks.site/marvels-spider-man-2/ 64.5
# https://paste.fitgirl-repacks.site/?aa7ee62c43546e4f#HdgTUYUKFGRt2uVMyfx4i2KaZ8eS31oLoUJwzMaZqKJ7
# https://filecrypt.cc/Container/132FA1060B.html Marvels.Spider-Man.2.Update.v1.318.1.0-RUNE (2 parts) (
# https://filecrypt.cc/Container/6BC10C41DF.html Marvels.Spider-Man.2.Update.v1.526.0.0-RUNE.rar

# https://fitgirl-repacks.site/uncharted-legacy-of-thieves-collection/19.6 GB
# https://paste.fitgirl-repacks.site/?a993186f66aa6b9b#4vELwJVmcZgxCyxR2BEEJXU9wuekVn6DWrAVXZKuhwGG
# https://datanodes.to/wg1culzx97v0/Uncharted_LoTC_Update_from_v1.0.20122_to_v1.3.20900_by_ElAmigos.exe
# https://datanodes.to/pizdmigzksj1/Uncharted_LoTC_Update_from_v1.3.20900_to_v1.4.21058_by_ElAmigos.exe

# dishonered 2 >> torrent
# https://1337x.to/torrent/3471850/Dishonored-2-v1-77-9-DLC-Bethesda-net-Bonus-MULTi9-FitGirl-Repack-Selective-Download-from-20-GB/

# The Elder Scrolls V: Skyrim – Anniversary Edition – v1.6.318.0.8 + All DLCs + CC Mods + Bonus Content
# https://paste.fitgirl-repacks.site/?deff4c912511b154#4aKskhfNC5cytWgfsYQgz3b9dZZaHeqGSgjb8DzgT3Ci


links = [x.strip() for x in link_inputs.splitlines() if x.strip()]
links

urls_to_process = []

for link_input in links:
  if link_input.startswith('https://paste.fitgirl'):
    driver.get(link_input)
    wait = WebDriverWait(driver, 10) # Wait up to 10 seconds
    # time.sleep(1)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[target="_blank"]')))
    urls_to_process = [elem.get_attribute('href') for elem in driver.find_elements(By.CSS_SELECTOR,'a[target="_blank"]')]
    # print('paste')

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
