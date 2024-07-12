#!/usr/bin/env python3

import re
import sqlite3
from pathlib import Path
from datetime import datetime

# Get the path to the IERS data directory.
# To obtain delta T values, only bulletin A files are needed.
PROJ_PATH = Path(__file__).resolve().parent.parent
IERS_PATH = PROJ_PATH / 'IERS'

BULLETIN_A_PATH = IERS_PATH / 'bulletinA'
assert BULLETIN_A_PATH.exists()


# Performance is not the first priority.
# There must be spaces for optimization of following functions,
# but they are not necessary.


def list_files() -> list[Path]:
  def __valid(p: str) -> bool:
    if not p.is_file():
      return False
    return re.match(r'^bulletina-.*\.txt$', p.name) is not None

  return list(filter(__valid, BULLETIN_A_PATH.glob('**/*.txt')))


def sanity_check(text: str) -> bool:
  '''Check the assumptions of the Bulletin A data files.'''
  if 'DUT1= (UT1-UTC) transmitted with time signals' not in text:
    return False
  if ('TAI-UTC = ' not in text) and \
     ('TAI-UTC(BIPM) = ' not in text):
    return False
  if 'TT = TAI + 32.184 seconds' not in text:
    return False
  return True


def find_date(text: str) -> datetime:
  '''Find the date line of a given Bulletin A data file and return the date.'''
  # Some examples of the expected lines that reveal the dates:
  # 17 November 2005                                    Vol. XVIII No. 046
  # 11 January 2007                                        Vol. XX No. 002
  # 14 February 2019                                    Vol. XXXII No. 007
  # 28 November 2019                                    Vol. XXXII No. 048
  # 26 January 2023                                     Vol. XXXVI No. 004

  for line in text.splitlines():
    stripped = line.strip()
    if re.match(r'^\d+\s+\w+\s+\d+\s+Vol\.\s+[IVXLCDM]+\s+No\.\s+\d+$', stripped):
      date_strs = stripped.split()[:3]
      return datetime.strptime(' '.join(date_strs), '%d %B %Y')
  raise ValueError('No date line found in lines')


def dut1(text: str) -> tuple[float, datetime]:
  '''Return the DUT1 value and the datetime that the DUT1 value starts to be effective.'''
  # Example:
  # DUT1= (UT1-UTC) transmitted with time signals                    
  #     =  +0.0 seconds beginning 22 Aug 2013 at 0000 UTC

  def __get_dut1_dt_str() -> str:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
      if 'DUT1= (UT1-UTC) transmitted with time signals' in line:
        return lines[idx + 1].split('=')[-1].strip()

  dut1_dt_str = __get_dut1_dt_str()

  pattern = r'([+-]?\d+\.\d+)\s+seconds\s+beginning\s+([\d\s\w]+)\s+UTC'
  matches = re.search(pattern, dut1_dt_str, re.VERBOSE)
  assert matches

  # Check the spell of the month.
  # Some are of this format: 11 April 2013 at 0000
  # Some are of this format: 22 Aug 2013 at 0000'
  dt_str = matches.group(2)
  short_spelled = (len(dt_str.split()[1]) <= 3)
  month_formatter = '%b' if short_spelled else '%B'

  dut1 = float(matches.group(1))
  dt = datetime.strptime(dt_str, f'%d {month_formatter} %Y at %H%M')
  return (dut1, dt)


def tai_utc(text: str) -> tuple[float, datetime]:
  '''Return the TAI-UTC value and the datetime that the TAI-UTC value starts to be effective.'''
  # Example:
  # Beginning 1 July 2012:                                                
  #    TAI-UTC = 35.000 000 seconds

  def __get_tai_utc_dt_lines() -> tuple[str, str]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
      if 'TAI-UTC = ' in line or 'TAI-UTC(BIPM) = ' in line:
        assert '000 seconds' in line
        assert len(line.strip().split()) == 5
        prev_line = lines[idx - 1]
        assert 'Beginning' in prev_line
        return prev_line.strip(), line.strip()

  dt_line, tai_utc_line = __get_tai_utc_dt_lines()

  # Check the spell of the month.
  # Some are of this format: 11 April 2013
  # Some are of this format: 22 Aug 2013
  month_str = dt_line.split()[-2]
  short_spelled = (len(month_str) <= 3)
  month_formatter = '%b' if short_spelled else '%B'

  # Some `dt_line`s end with ':', some not...
  datetime_formatter = f'Beginning %d {month_formatter} %Y'
  if dt_line.endswith(':'):
    datetime_formatter += ':'

  dt = datetime.strptime(dt_line, datetime_formatter)

  # Use `re` to pick all digits and dots from `tai_utc_line`.
  fraction = tai_utc_line.strip().split()[2:4]
  tai_utc = float(''.join(fraction))

  return (tai_utc, dt)


def do_sanity_checks() -> bool:
  texts = map(Path.read_text, list_files())
  checks = map(sanity_check, texts)
  return all(checks)


def gen_dut1_db() -> None:
  assert do_sanity_checks()

  texts = list(map(Path.read_text, list_files()))
  datetimes = list(map(find_date, texts))
  dut1s = map(dut1, texts)

  DELTA_T_PATH = Path(__file__).parent

  dut1_path = DELTA_T_PATH / 'dut1.sqlite3'
  assert not dut1_path.exists()

  # Create dut1 table, the keys are:
  #   report_date:    string, datetime of iso format
  #   dut1:           float
  #   effective_from: string, datetime of iso format
  conn_dut1 = sqlite3.connect(dut1_path)
  conn_dut1.execute('CREATE TABLE dut1 (report_date DATETIME, dut1 REAL, effective_from DATETIME)')
 
  for report_dt, (dut1_value, effective_from) in zip(datetimes, dut1s):
    conn_dut1.execute('INSERT INTO dut1 VALUES (?, ?, ?)', 
                      (report_dt.isoformat(), dut1_value, effective_from.isoformat()))

  conn_dut1.commit()
  conn_dut1.close()


def gen_tai_utc_db() -> None:
  assert do_sanity_checks()

  texts = list(map(Path.read_text, list_files()))
  datetimes = list(map(find_date, texts))
  tai_utcs = map(tai_utc, texts)

  DELTA_T_PATH = Path(__file__).parent

  tai_utc_path = DELTA_T_PATH / 'tai_utc.sqlite3'
  assert not tai_utc_path.exists()

  # Create tai_utc table, the keys are:
  #   report_date:    string, datetime of iso format
  #   tai_utc:        float
  #   effective_from: string, datetime of iso format
  conn_tai_utc = sqlite3.connect(tai_utc_path)
  conn_tai_utc.execute('CREATE TABLE tai_utc (report_date DATETIME, tai_utc REAL, effective_from DATETIME)')

  for report_dt, (tai_utc_value, effective_from) in zip(datetimes, tai_utcs):
    conn_tai_utc.execute('INSERT INTO tai_utc VALUES (?, ?, ?)', 
                         (report_dt.isoformat(), tai_utc_value, effective_from.isoformat()))

  conn_tai_utc.commit()
  conn_tai_utc.close()


if __name__ == '__main__':
  assert do_sanity_checks()
  gen_dut1_db()
  gen_tai_utc_db()
