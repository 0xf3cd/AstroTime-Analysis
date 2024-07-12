#!/usr/bin/env python3
# Copyright (c) 2024, 0xf3cd <https://github.com/0xf3cd>.
# Analysis on the Bulletin A data files, for delta T values.

import re

from pathlib import Path
from itertools import chain, count
from datetime import datetime
from dataclasses import dataclass

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


def sanity_checks() -> bool:
  def __sanity_check(text: str) -> bool:
    '''Check the assumptions of the Bulletin A data files.'''

    if 'DUT1= (UT1-UTC) transmitted with time signals' not in text:
      return False
    if ('TAI-UTC = ' not in text) and \
      ('TAI-UTC(BIPM) = ' not in text):
      return False
    if 'TT = TAI + 32.184 seconds' not in text:
      return False
    
    if 'IERS Rapid Service' not in text:
      return False
    if 'MJD      x    error     y    error   UT1-UTC   error' not in text:
      return False
    
    if 'IERS Final Values' in text:
      if 'MJD        x        y      UT1-UTC' not in text:
        return False
    
    return True
  
  texts = map(Path.read_text, list_files())
  results = map(__sanity_check, texts)
  return all(results)


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


#region Header Parser

def header_dut1(text: str) -> tuple[float, datetime]:
  '''
  Return the DUT1 value and the datetime that the DUT1 value starts to be effective.
  The DUT1 value is extracted from bulletin A file's header, which is very precise.
  Precise values can be retrieved from the "Rapid Service" or "Final Values" section of the Bulletin A file.
  '''
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


def header_tai_utc(text: str) -> tuple[float, datetime]:
  '''
  Return the TAI-UTC value and the datetime that the TAI-UTC value starts to be effective.
  The value is read from bulletin A file's header.
  '''
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


@dataclass
class Header:
  report_time: datetime
  dut1: float
  dut1_effective: datetime
  tai_utc: float
  tai_utc_effective: datetime


def extract_header(text: str) -> Header:
  report_time = find_date(text)
  dut1, dut1_effective = header_dut1(text)
  tai_utc, tai_utc_effective = header_tai_utc(text)
  return Header(report_time, dut1, dut1_effective, tai_utc, tai_utc_effective)


#region Repid Service Parser

def rapid_service_data_lines(text: str) -> list[str]:
  '''Return the lines in the "Rapid Service" section of the Bulletin A file.'''

  lines = text.splitlines()
  for idx, line in enumerate(lines):
    # The Rapid Service section is expected to contain the following line,
    # which reveals the column names of the data:
    if 'MJD      x    error     y    error   UT1-UTC   error' in line:
      unit_line = lines[idx + 1]
      assert '"' in unit_line
      assert 's' in unit_line

      # The lines right after `unit_line` are the data lines.
      # There can be 6 or 7 lines.
      data_lines = []
      for line_no in count(idx + 2):
        dl = lines[line_no].strip()
        if dl == '':
          break
        if set(dl) == {'-'} or set(dl) == {'*'}:
          break
        data_lines.append(dl)

      for dl in data_lines: # Some extra sanity checks.
        assert len(dl.split()) == 10, f'Invalid line: {dl}'

      return data_lines
    
  raise ValueError('No "Rapid Service" section found in lines')


@dataclass
class RapidService:
  mjd: int
  x: float
  x_err: float
  y: float
  y_err: float
  ut1_utc: float
  ut1_utc_err: float


def extract_rapid_service(text: str):  
  def __parse(dl: str) -> RapidService:
    splitted = dl.split()
    assert len(splitted) == 10

    mjd = int(splitted[3])
    x = float(splitted[4])
    x_err = float(splitted[5])
    y = float(splitted[6])
    y_err = float(splitted[7])
    ut1_utc = float(splitted[8])
    ut1_utc_err = float(splitted[9])

    return RapidService(mjd, x, x_err, y, y_err, ut1_utc, ut1_utc_err)

  data_lines = rapid_service_data_lines(text)
  return map(__parse, data_lines)


#region Final Values Parser

def contains_final_values(text: str) -> bool:
  return 'Final Values' in text and 'MJD        x        y      UT1-UTC' in text


def final_values_lines(text: str) -> list[str]:
  assert contains_final_values(text)

  lines = text.splitlines()
  for idx, line in enumerate(lines):
    if 'MJD        x        y      UT1-UTC' in line:
      unit_line = lines[idx + 1]
      assert '"' in unit_line
      assert 's' in unit_line

      # The lines right after `unit_line` are the data lines.
      data_lines = []
      for line_no in count(idx + 2):
        dl = lines[line_no].strip()
        if dl == '':
          break
        if set(dl) == {'-'} or set(dl) == {'*'}:
          break
        data_lines.append(dl)

      for dl in data_lines: # Some extra sanity checks.
        assert len(dl.split()) == 7, f'Invalid line: {dl}'

      return data_lines

  raise ValueError('No "Final Values" section found in lines')


@dataclass
class FinalValue:
  mjd: int
  x: float
  y: float
  ut1_utc: float

def extract_final_values(text: str):
  def __parse(dl: str) -> FinalValue:
    splitted = dl.split()
    assert len(splitted) == 7

    mjd = int(splitted[3])
    x = float(splitted[4])
    y = float(splitted[5])
    ut1_utc = float(splitted[6])

    return FinalValue(mjd, x, y, ut1_utc)

  data_lines = final_values_lines(text)
  return map(__parse, data_lines)


#region CVS file saving

DELTA_T_PATH = Path(__file__).parent
CVS_PATH = DELTA_T_PATH / 'cvs'

def ensure_cvs_path():
  CVS_PATH.mkdir(exist_ok=True)


def save_header_cvs() -> None:
  '''Parse the headers of bulletin A files, and save the header information to a CVS file.'''
  texts       = map(Path.read_text, list_files())
  headers     = map(extract_header, texts)
  header_info = sorted(headers, key=lambda h: h.report_time)

  # The CVS file has the following columns:
  # report_time          - datetime when the bulletin A file is issued
  # dut1                 - the dut1 value read from the header
  # dut1_effective_dt    - datetime when the dut1 value becomes effective
  # tai_utc              - the tai_utc value read from the header
  # tai_utc_effective_dt - datetime when the tai_utc value becomes effective

  ensure_cvs_path()
  cvs_file = CVS_PATH / 'bulletin_a_header.csv'

  with cvs_file.open('w') as f:
    f.write('report_time,dut1,dut1_effective_dt,tai_utc,tai_utc_effective_dt\n')
    for h in header_info:
      f.write(f'{h.report_time.isoformat()},{h.dut1},{h.dut1_effective.isoformat()},{h.tai_utc},{h.tai_utc_effective.isoformat()}\n')


def save_rapid_service_cvs() -> None:
  '''
  Parse the UT1-UTC values from the Rapid Service section of bulletin A files, and save the values to a CVS file.
  The values are expected to be more accurate than the DUT1 values in headers.
  '''
  texts = map(Path.read_text, list_files())
  data = map(extract_rapid_service, texts)
  chained_data = chain.from_iterable(data)
  rapid_service = sorted(chained_data, key=lambda d: d.mjd)

  # The CVS file has the following columns:
  # mjd                  - modified julian date
  # x                    - the x value, unit: ""
  # x_err                - the x value error, unit: ""
  # y                    - the y value read, unit: ""
  # y_err                - the y value error, unit: ""
  # ut1_utc              - the ut1_utc value, unit: s
  # ut1_utc_err          - the ut1_utc value error, unit: s

  ensure_cvs_path()
  cvs_file = CVS_PATH / 'bulletin_a_rapid_service.csv'

  with cvs_file.open('w') as f:
    f.write('mjd,x,x_err,y,y_err,ut1_utc,ut1_utc_err\n')
    for d in rapid_service:
      f.write(f'{d.mjd},{d.x},{d.x_err},{d.y},{d.y_err},{d.ut1_utc},{d.ut1_utc_err}\n')


def save_final_values_cvs() -> None:
  '''Parse the final values from the Final Values section of bulletin A files, and save the values to a CVS file.'''
  texts = filter(
    contains_final_values,
    map(Path.read_text, list_files()),
  )

  data = map(extract_final_values, texts)
  chained_data = chain.from_iterable(data)
  final_values = sorted(chained_data, key=lambda d: d.mjd)

  ensure_cvs_path()
  cvs_file = CVS_PATH / 'bulletin_a_final_values.csv'

  with cvs_file.open('w') as f:
    f.write('mjd,x,y,ut1_utc\n')
    for d in final_values:
      f.write(f'{d.mjd},{d.x},{d.y},{d.ut1_utc}\n')


def read_header_cvs() -> list[Header]:
  ret: list[Header] = []

  with (CVS_PATH / 'bulletin_a_header.csv').open('r') as f:
    lines = f.read().strip().splitlines()
    for l in lines[1:]:
      report_time, dut1, dut1_effective_dt, tai_utc, tai_utc_effective_dt = l.split(',')
      ret.append(Header(
        report_time=datetime.fromisoformat(report_time),
        dut1=float(dut1),
        dut1_effective=datetime.fromisoformat(dut1_effective_dt),
        tai_utc=float(tai_utc),
        tai_utc_effective=datetime.fromisoformat(tai_utc_effective_dt),
      ))
  
  return sorted(ret, key=lambda h: h.report_time)


def read_rapid_service_cvs() -> list[RapidService]:
  ret: list[RapidService] = []

  with (CVS_PATH / 'bulletin_a_rapid_service.csv').open('r') as f:
    lines = f.read().strip().splitlines()
    for l in lines[1:]:
      mjd, x, x_err, y, y_err, ut1_utc, ut1_utc_err = l.split(',')
      ret.append(RapidService(
        mjd=int(mjd),
        x=float(x),
        x_err=float(x_err),
        y=float(y),
        y_err=float(y_err),
        ut1_utc=float(ut1_utc),
        ut1_utc_err=float(ut1_utc_err),
      ))

  return sorted(ret, key=lambda d: d.mjd)


def read_final_value_cvs() -> list[FinalValue]:
  ret: list[FinalValue] = []

  with (CVS_PATH / 'bulletin_a_final_values.csv').open('r') as f:
    lines = f.read().strip().splitlines()
    for l in lines[1:]:
      mjd, x, y, ut1_utc = l.split(',')
      ret.append(FinalValue(
        mjd=int(mjd),
        x=float(x),
        y=float(y),
        ut1_utc=float(ut1_utc),
      ))

  return sorted(ret, key=lambda d: d.mjd)


if __name__ == '__main__':
  assert sanity_checks()

  save_header_cvs()
  read_header_cvs() # For sanity check purpose.

  save_rapid_service_cvs()
  read_rapid_service_cvs() # For sanity check purpose.

  save_final_values_cvs()
  read_final_value_cvs()
