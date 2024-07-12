#!/usr/bin/env python3

import pprint
import asyncio
import requests

from pathlib import Path
from dataclasses import dataclass

from typing import Sequence


@dataclass
class FileMetadata:
  path: Path
  url:  str

def download(fm: FileMetadata) -> bool:
  '''
  Download a file from url and save it to path.
  Returns True if the download was successful, False otherwise.
  '''

  try:
    if not fm.path.parent.exists():
      fm.path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(fm.url, stream=True) as r:
      r.raise_for_status()
      with open(fm.path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
          f.write(chunk)

  except Exception as e:
    print(f'Error downloading {fm.url}: {e}')
    return False
  
  print(f'OK downloaded {fm.url}')
  return True



class AsyncDownloader:
  def __init__(self, files: Sequence[FileMetadata], parallel: int = 8) -> None:
    self._queue = asyncio.Queue()
    for f in files:
      self._queue.put_nowait(f)

    self._failed_files = asyncio.Queue()
    self._parallel = parallel

  async def __download(self, fm: FileMetadata) -> None:
    loop = asyncio.get_running_loop()
    ret = await loop.run_in_executor(None, download, fm)
    if not ret:
      await self._failed_files.put(fm)
  
  async def __coro(self) -> None:
    while not self._queue.empty():
      fm = await self._queue.get()
      await self.__download(fm)

  async def run(self) -> None:
    tasks = [self.__coro() for _ in range(self._parallel)]
    await asyncio.gather(*tasks)

  def failed_files(self) -> list[FileMetadata]:
    ret = []
    while not self._failed_files.empty():
      ret.append(self._failed_files.get_nowait())
    return ret


IERS_PATH = Path(__file__).parent
assert IERS_PATH.exists()

BULLETIN_A_PATH = IERS_PATH / 'bulletinA'
BULLETIN_A_PATH.mkdir(exist_ok=True)

BULLETIN_B_PATH = IERS_PATH / 'bulletinB'
BULLETIN_B_PATH.mkdir(exist_ok=True)

BULLETIN_C_PATH = IERS_PATH / 'bulletinC'
BULLETIN_C_PATH.mkdir(exist_ok=True)

BULLETIN_D_PATH = IERS_PATH / 'bulletinD'
BULLETIN_D_PATH.mkdir(exist_ok=True)


#region Bulletin A

BULLETIN_A_FILE_METADATA = {
# year, (year_roman, file_count)
  2005: ('xviii',    52),
  2006: ('xix',      52),
  2007: ('xx',       52),
  2008: ('xxi',      53),
  2009: ('xxii',     52),
  2010: ('xxiii',    52),
  2011: ('xxiv',     52),
  2012: ('xxv',      52),
  2013: ('xxvi',     52),
  2014: ('xxvii',    52),
  2015: ('xxviii',   53),
  2016: ('xxix',     52),
  2017: ('xxx',      52),
  2018: ('xxxi',     52),
  2019: ('xxxii',    52),
  2020: ('xxxiii',   53),
  2021: ('xxxiv',    52),
  2022: ('xxxv',     52),
  2023: ('xxxvi',    52),
  2024: ('xxxvii',   28), # As of 2024-Jul-11 PST, only 28 files are available for 2024.
}

def bulletin_a_files() -> list[FileMetadata]:
  ret = []
  for year, (year_roman, file_count) in BULLETIN_A_FILE_METADATA.items():
    for file_number in range(1, file_count + 1):
      fn   = f'bulletina-{year_roman}-{file_number:03}.txt'
      url  = f'https://datacenter.iers.org/data/6/{fn}'
      path = IERS_PATH / 'bulletinA' / str(year) / fn
      ret.append(FileMetadata(path, url))
  return ret

def bulletin_a_undownloaded_files() -> list[FileMetadata]:
  return [f for f in bulletin_a_files() if not f.path.exists()]


#region Bulletin B

BULLETIN_B_FIRST_FILE_NUMBER = 253
BULLETIN_B_LAST_FILE_NUMBER  = 437

def bulletin_b_files() -> list[FileMetadata]:
  ret = []
  for file_number in range(BULLETIN_B_FIRST_FILE_NUMBER, BULLETIN_B_LAST_FILE_NUMBER + 1):
    fn   = f'bulletinb-{file_number:03}.txt'
    url  = f'https://datacenter.iers.org/data/207/{fn}'
    path = IERS_PATH / 'bulletinB' / fn
    ret.append(FileMetadata(path, url))
  return ret

def bulletin_b_undownloaded_files() -> list[FileMetadata]:
  return [f for f in bulletin_b_files() if not f.path.exists()]


#region Bulletin C

BULLETIN_C_FIRST_FILE_NUMBER = 10
BULLETIN_C_LAST_FILE_NUMBER  = 68

def bulletin_c_files() -> list[FileMetadata]:
  ret = []
  for file_number in range(BULLETIN_C_FIRST_FILE_NUMBER, BULLETIN_C_LAST_FILE_NUMBER + 1):
    fn   = f'bulletinc-{file_number:03}.txt'
    url  = f'https://datacenter.iers.org/data/16/{fn}'
    path = IERS_PATH / 'bulletinC' / fn
    ret.append(FileMetadata(path, url))
  return ret

def bulletin_c_undownloaded_files() -> list[FileMetadata]:
  return [f for f in bulletin_c_files() if not f.path.exists()]


#region Bulletin D

BULLETIN_D_FIRST_FILE_NUMBER = 21
BULLETIN_D_LAST_FILE_NUMBER  = 142

def bulletin_d_files() -> list[FileMetadata]:
  ret = []
  for file_number in range(BULLETIN_D_FIRST_FILE_NUMBER, BULLETIN_D_LAST_FILE_NUMBER + 1):
    fn   = f'bulletind-{file_number:03}.txt'
    url  = f'https://datacenter.iers.org/data/17/{fn}'
    path = IERS_PATH / 'bulletinD' / fn
    ret.append(FileMetadata(path, url))
  return ret

def bulletin_d_undownloaded_files() -> list[FileMetadata]:
  return [f for f in bulletin_d_files() if not f.path.exists()]


#region Main

if __name__ == '__main__':
  print(f'Using {IERS_PATH}')

  downloader_a = AsyncDownloader(bulletin_a_undownloaded_files())
  downloader_b = AsyncDownloader(bulletin_b_undownloaded_files())
  downloader_c = AsyncDownloader(bulletin_c_undownloaded_files())
  downloader_d = AsyncDownloader(bulletin_d_undownloaded_files())

  asyncio.run(downloader_a.run())
  asyncio.run(downloader_b.run())
  asyncio.run(downloader_c.run())
  asyncio.run(downloader_d.run())

  failed_files = downloader_a.failed_files() + downloader_b.failed_files() \
               + downloader_c.failed_files() + downloader_d.failed_files()

  print('-' * 60)
  print('Failed files:')
  pprint.pprint([f.url for f in failed_files])
