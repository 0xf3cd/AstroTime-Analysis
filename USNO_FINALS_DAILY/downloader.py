#!/usr/bin/env python3
# Copyright (c) 2024, 0xf3cd <https://github.com/0xf3cd>
#
# Downloader for `finals.daily` from USNO.
# Ref: https://maia.usno.navy.mil/products/daily.htm

import requests
from pathlib import Path

DAILY_DATA_URL = 'https://maia.usno.navy.mil/ser7/finals.daily.extended'
README_URL = 'https://maia.usno.navy.mil/ser7/readme.finals'
DELTAT_PREDS_URL = 'https://maia.usno.navy.mil/ser7/deltat.preds'

USNO_DIR = Path(__file__).parent.resolve()

if __name__ == '__main__':
  with requests.get(DAILY_DATA_URL, stream=True) as r:
    r.raise_for_status()

    daily_file = USNO_DIR / DAILY_DATA_URL.split('/')[-1]
    with open(daily_file, 'wb') as f:
      for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)

  print(f'OK downloaded {DAILY_DATA_URL}')

  with requests.get(README_URL) as r:
    r.raise_for_status()

    readme_file = USNO_DIR / README_URL.split('/')[-1]
    with open(readme_file, 'w') as f:
      f.write(r.text)

  print(f'OK downloaded {README_URL}')

  with requests.get(DELTAT_PREDS_URL) as r:
    r.raise_for_status()

    preds_file = USNO_DIR / DELTAT_PREDS_URL.split('/')[-1]
    with open(preds_file, 'wb') as f:
      f.write(r.content)

  print(f'OK downloaded {DELTAT_PREDS_URL}')
