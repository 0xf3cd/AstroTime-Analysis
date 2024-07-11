# IERS Data
> This folder contains the data downloaded from IERS.

## Bulletin A
* Each file from bulletin A consists of 4 sections:
> section 1: DUT1 [sec], TAI-UTC [sec]

> section 2: x [''], y [''], UT1-UTC [sec] and their errors

> section 3: Predictions for x [''], y [''], UT1-UTC [sec]

> section 4: dpsi, deps, dX, dY ([msec of arc]) and their errors

* File `bulletina-xviii-005.txt` is missing on their website, so it was unable to be downloaded.


## Bulletin B
* Each file from bulletin B consists of 5 sections:
> Section 1: Year[yyyy],Month [mm], Day [dd], MJD, x [marcsec], y [marcsec], UT1-UTC [ms], dX [marcsec], dY [marcsec],x err[marcsec], y err[marcsec],UT1 err[marcsec], X err[marcsec], Y err[marcsec],

> Section 2: Year[yyyy],Month [mm], Day [dd], MJD, dPsi1980[marcsec],dEps1980[marcsec],sig dPsi[marcsec],sig dEps[marcsec]

> Section 3: Year[yyyy],Month [mm], Day [dd], MJD,LOD[ms],sigma[ms],OMEGA[mas/ms],sigma[mas/ms],

> Section 4: TAI - UTC [s],

> Section 5: RMS of x [marcsec], y [mas ], UT1 [ms], LOD[ms], dX [marcsec], dY [marcsec], Number of points


## Bulletin C
* Each file from bulletin C contains the delta value of `UTC-TAI` [s].


## Bulletin D
* Each file from bulletin C contains the delta value of `UT1-UTC` [s].

* The following files are missing from their website
``` Python
['bulletind-025.txt', 'bulletind-026.txt', 'bulletind-027.txt', 'bulletind-029.txt', 'bulletind-034.txt', 'bulletind-035.txt', 'bulletind-038.txt', 'bulletind-042.txt', 'bulletind-045.txt', 'bulletind-047.txt', 'bulletind-048.txt', 'bulletind-049.txt']
```
