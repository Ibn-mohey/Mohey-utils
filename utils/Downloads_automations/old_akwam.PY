# https://akwam.it/old/108611/%D9%85%D8%B3%D9%84%D8%B3%D9%84-%D8%B9%D8%A7%D8%A6%D9%84%D8%A9-%D8%A7%D9%84%D8%AD%D8%A7%D8%AC-%D9%86%D8%B9%D9%85%D8%A7%D9%86-HD

%pip install -q google-colab-selenium webdriver-manager
import google_colab_selenium as gs

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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
from urllib.parse import urljoin

driver = gs.Chrome()
links = input().splitlines()
while '' in links:
  links.remove('')
links = list(set(links))
  
wait = WebDriverWait(driver, 10) # Wait up to 10 seconds
final_links = set()
for link in links:
  driver.get(link)
  time.sleep(2)
  
  # Remove anti-adblock overlays
  driver.execute_script("""
    var el = document.getElementById('ignielAdBlock');
    if(el) el.remove();
    var el2 = document.getElementById('ofc9');
    if(el2) el2.remove();
    var el3 = document.getElementById('babasbmsgx');
    if(el3) el3.remove();
    document.body.style.overflow = 'auto';
    document.body.style.visibility = 'visible';
  """)
  
  try:
    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[target="framename"]')))
    href = element.get_attribute('href')
    if href and href not in final_links:
      final_links.add(href)
      print(href)
  except:
    # Fallback: try finding download links by other selectors
    try:
      elements = driver.find_elements(By.CSS_SELECTOR, '.direct_link_box a')
      for el in elements:
        href = el.get_attribute('href')
        if href and href not in final_links:
          final_links.add(href)
          print(href)
    except:
      print(f"Could not find links on: {link}")
# driver.quit()

print(f"\n--- Final unique links ({len(final_links)}) ---")
for l in final_links:
  print(l)