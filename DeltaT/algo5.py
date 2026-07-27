#!/usr/bin/env python3
# Copyright (c) 2026, 0xf3cd <https://github.com/0xf3cd>
# Fit "algo5" for celestial-calendar's `delta_t.hpp`.
#
# Methodology (successor of algo4, see `models.ipynb`):
#   Segment 1 (2005.0 <= year <= YEAR_ANCHOR):
#     Polynomial of the same functional form as algo4's first segment
#     (u = year - 1990; terms 1, 1/u, u, u^2, ..., u^6), fitted on IERS
#     Bulletin A final values (observations). Unlike algo4, the fit window
#     runs all the way to the last available observation, so there is no
#     separate prediction-trained segment and no seam at 2024.0.
#   Segment 2 (year > YEAR_ANCHOR):
#     Stephenson-Morrison-Hohenkerk integrated-lod curve (UKHO "lvm" model,
#     https://astro.ukho.gov.uk/nao/lvm/):
#       lod  = 1.72*t - 3.5*sin(2*pi*(t + 0.75)/14)   [ms/day], t = (year-1825)/100
#       DT   = C + 31.4115*t^2 + 284.8435805251424*cos(0.4487989505128276*(t + 0.75))
#     The integration constant C is chosen so segment 2 equals segment 1 at
#     YEAR_ANCHOR -> continuous by construction, valid for all future years.
#
# The observation series is built exactly like models.ipynb: Bulletin A final
# values, TAI-UTC from headers (1999 typo discarded), DT = TAI-UTC - (UT1-UTC)
# + 32.184, outliers removed by a degree-3 poly fit and a 2-sigma cut.

import sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyzer import read_header_cvs, read_final_value_cvs  # noqa: E402


#region Observation series (replicates models.ipynb cells 1-10)

def build_series() -> tuple[np.ndarray, np.ndarray]:
  tai_utc_pairs = sorted(
    set((h.tai_utc, h.tai_utc_effective) for h in read_header_cvs()),
    key=lambda p: p[1],
  )
  # models.ipynb: "(33.0, 1999-01-01)" is believed to be a typo in the IERS file.
  tai_utc_pairs = [p for p in tai_utc_pairs if p != (33.0, datetime(1999, 1, 1))]

  def mjd_to_dt(mjd: int) -> datetime:
    return datetime(1858, 11, 17) + timedelta(days=mjd)

  def dt_to_year(dt: datetime) -> float:
    year = dt.year
    year_length = datetime(year + 1, 1, 1).timestamp() - datetime(year, 1, 1).timestamp()
    return year + (dt.timestamp() - datetime(year, 1, 1).timestamp()) / year_length

  def find_tai_utc(dt: datetime) -> float:
    for tai_utc, effective in reversed(tai_utc_pairs):
      if effective <= dt:
        return tai_utc
    raise ValueError(f'No TAI-UTC value effective at {dt}')

  final_value_pairs = sorted(
    set((fv.ut1_utc, mjd_to_dt(fv.mjd)) for fv in read_final_value_cvs()),
    key=lambda p: p[1],
  )

  years, delta_ts = [], []
  for ut1_utc, dt in final_value_pairs:
    years.append(dt_to_year(dt))
    delta_ts.append(find_tai_utc(dt) - ut1_utc + 32.184)
  return np.array(years), np.array(delta_ts)


def filter_outliers(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
  # models.ipynb: degree-3 poly fit, discard residuals beyond 2 sigma.
  residuals = y - np.polyval(np.polyfit(x, y, 3), x)
  keep = np.abs(residuals) <= 2 * np.std(residuals)
  print(f'{np.count_nonzero(~keep)} outliers removed ({len(x)} -> {np.count_nonzero(keep)} points)')
  return x[keep], y[keep]


#region Fitting

def design_matrix(year: np.ndarray) -> np.ndarray:
  u = year - 1990.0
  return np.stack([np.ones_like(u), 1.0 / u, u, u**2, u**3, u**4, u**5, u**6], axis=1)


def fit_segment1(year: np.ndarray, delta_t: np.ndarray,
                 constraints: list[tuple[float, float]]) -> np.ndarray:
  # Constrained least squares: minimize ||A c - y||^2 subject to a(year_k) c = value_k.
  # An unconstrained fit flares at the window edges (~+0.13 s at the last observation), and
  # segment 2 would inherit the right-edge offset forever — the constraints pin the polynomial
  # to the actual observed Delta T at both served-domain edges. Solved via the KKT system:
  #   [2 A^T A  G^T] [c]      [2 A^T y]
  #   [   G      0 ] [lam]  = [values]
  a_mat = design_matrix(year)
  g_mat = design_matrix(np.array([c[0] for c in constraints]))
  values = np.array([c[1] for c in constraints])
  n, m = a_mat.shape[1], len(constraints)
  kkt = np.zeros((n + m, n + m))
  kkt[:n, :n] = 2.0 * a_mat.T @ a_mat
  kkt[:n, n:] = g_mat.T
  kkt[n:, :n] = g_mat
  rhs = np.concatenate([2.0 * a_mat.T @ delta_t, values])
  return np.linalg.solve(kkt, rhs)[:n]


def segment1(coeffs: np.ndarray, year) -> np.ndarray:
  return design_matrix(np.atleast_1d(np.asarray(year, dtype=float))) @ coeffs


def integrated_lod(year, c: float = 0.0):
  t = 0.01 * (np.asarray(year, dtype=float) - 1825.0)
  return c + 31.4115 * t * t + 284.8435805251424 * np.cos(0.4487989505128276 * (t + 0.75))


#region Main

if __name__ == '__main__':
  years, delta_ts = build_series()
  print(f'observation series: {len(years)} points, {years.min():.4f} .. {years.max():.4f}')

  # Robust anchors at both served-domain edges (daily UT1-UTC noise is a few ms; medians
  # of ~60-observation windows smooth it out).
  # Right edge: the year of the last observation — segment 2 starts here.
  # Left edge: 2005.0 — where algo5 takes over from algo2.
  order = np.argsort(years)
  year_anchor = float(years.max())
  dt_anchor = float(np.median(delta_ts[order][-60:]))
  near_2005 = np.abs(years - 2005.0) <= 30.0 / 365.25
  dt_2005 = float(np.median(delta_ts[near_2005]))
  print(f'right anchor: year {year_anchor!r}, delta_t {dt_anchor!r} (median of last 60 obs)')
  print(f'left  anchor: year 2005.0, delta_t {dt_2005!r} (median of obs within 30 days)')

  fx, fy = filter_outliers(years, delta_ts)
  coeffs = fit_segment1(fx, fy, [(2005.0, dt_2005), (year_anchor, dt_anchor)])

  pred = segment1(coeffs, fx)
  residuals = pred - fy
  served = fx >= 2005.0  # year < 2005 delegates to algo2; the 2004.85-2005.0 stretch is fit data only
  print(f'segment 1 fit: r2={1 - np.sum(residuals**2) / np.sum((fy - fy.mean())**2):.9f}')
  print(f'  mse={np.mean(residuals**2):.9f}  mae={np.mean(np.abs(residuals)):.9f}  '
        f'max_error={np.max(np.abs(residuals)):.9f}')
  print(f'  served domain (year >= 2005): mae={np.mean(np.abs(residuals[served])):.9f}  '
        f'max_error={np.max(np.abs(residuals[served])):.9f}')

  # Residual profile per year — watch for regional bias, especially the 2024-2026 tail
  # (that stretch feeds the anchor) and the window edges.
  print('\nresidual profile (fit - observed, per calendar year):')
  for y0 in range(2005, 2027):
    mask = (fx >= y0) & (fx < y0 + 1)
    if not mask.any():
      continue
    r = residuals[mask]
    print(f'  {y0}: n={mask.sum():4d}  mean={r.mean():+.4f}  mae={np.abs(r).mean():.4f}  max={np.abs(r).max():.4f}')

  c_anchor = float(dt_anchor - integrated_lod(year_anchor))
  print(f'\nYEAR_ANCHOR = {year_anchor!r}')
  print(f'C_ANCHOR    = {c_anchor!r}  (segment 2 integration constant)')

  names = ['1', '1/u', 'u', 'u^2', 'u^3', 'u^4', 'u^5', 'u^6']
  print('\nsegment 1 coefficients (u = year - 1990):')
  for name, c in zip(names, coeffs):
    print(f'  {name:>4}: {c!r}')

  def algo5(year):
    year = np.atleast_1d(np.asarray(year, dtype=float))
    return np.where(year <= year_anchor,
                    segment1(coeffs, year),
                    integrated_lod(year, c_anchor))

  def algo4_segment1(year: float) -> float:
    u = year - 1990.0
    return (-1539.5103964825782 + 7305.087465383047 / u + 116.17205714035308 * u
            - 1.1279910329686536 * u**2 - 0.2754809577876994 * u**3
            + 0.01542796862306066 * u**4 - 0.0003332548091334704 * u**5
            + 2.6541070013360904e-06 * u**6)

  # Continuity / seam report.
  eps = 1e-9
  print(f'\nseam at YEAR_ANCHOR: {float(algo5(year_anchor + eps)[0] - algo5(year_anchor - eps)[0]):+.2e} s (by construction ~0)')
  algo2_2005 = 62.92 + 0.32217 * 5.0 + 0.005589 * 25.0  # espenak-meeus 2005-2050 branch
  print(f'seam at 2005.0 vs algo2: algo5 {float(algo5(2005.0)[0]) - algo2_2005:+.4f} s, '
        f'algo4 {algo4_segment1(2005.0) - algo2_2005:+.4f} s')
  print(f'algo5 vs algo4 at 2005.0: {float(algo5(2005.0)[0]) - algo4_segment1(2005.0):+.4f} s')

  # Reference values for C++ golden tests.
  print('\nreference values (year -> algo5):')
  for y in [2005.0, 2010.0, 2015.0, 2020.0, 2024.0, 2025.0, 2026.0, year_anchor,
            2027.0, 2030.0, 2035.0, 2050.0, 2100.0, 2200.0]:
    print(f'  {y}: {float(algo5(y)[0])!r}')
