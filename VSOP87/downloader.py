#!/usr/bin/env python3
# Copyright (c) 2024, 0xf3cd <https://github.com/0xf3cd>
#
# Downloader for VSOP87 tables.
# Ref: https://cdsarc.cds.unistra.fr/ftp/VI/81/


import requests
from pathlib import Path

from bs4 import BeautifulSoup

DOWNLOAD_URL = 'https://cdsarc.cds.unistra.fr/ftp/VI/81/'

VSOP87_DIR = Path(__file__).parent.resolve() / 'downloaded'
VSOP87_DIR.mkdir(exist_ok=True)

if __name__ == '__main__':
  # List all files provided, using BeautifulSoup.
  soup = BeautifulSoup(requests.get(DOWNLOAD_URL).text, 'html.parser')

  for a in soup.find_all('a'):
    href = a['href']
    if href.startswith('/'):
      continue

    url = DOWNLOAD_URL + href
    file = VSOP87_DIR / href
    with open(file, 'wb') as f:
      for chunk in requests.get(url, stream=True).iter_content(chunk_size=8192):
        f.write(chunk)
