"""Physical values, projection and narrative interpolation. Time is film time only."""
import csv
from bisect import bisect_right
from dataclasses import dataclass
from math import log10, sqrt
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicHermiteSpline, PchipInterpolator

ROOT = Path(__file__).resolve().parent
with (ROOT / "track.csv").open(encoding="utf8") as f:
    TRACK = list(csv.DictReader(f))
TIMES = [float(r["time"]) for r in TRACK]
TSUN = 5772
TMIN, TMAX = 2500, 140000
LMIN, LMAX = 0.0001, 1e5
LEFT, RIGHT, TOP, BOTTOM = 156, 1126, 231, 766

@dataclass(frozen=True)
class Star:
    phase: str
    temperature: float
    luminosity: float
    gas_progress: float = 0.0

    @property
    def radius(self):
        return sqrt(self.luminosity) * (TSUN / self.temperature) ** 2

def hr_to_point(t, l):
    u = log10(TMAX / t) / log10(TMAX / TMIN)
    v = log10(l / LMIN) / log10(LMAX / LMIN)
    return LEFT + (RIGHT - LEFT) * u, BOTTOM - (BOTTOM - TOP) * v

def display_radius(r):
    # One fixed monotonic compression for all physical stars in the film.
    return 41 * r ** 0.29

_temp=np.log([float(r["temperature_K"]) for r in TRACK])
_lum=np.log([float(r["luminosity_Lsun"]) for r in TRACK])
_temperature=PchipInterpolator(TIMES,_temp)
_slopes=PchipInterpolator(TIMES,_lum).derivative()(TIMES)
# Couple the two cooling splines so the small radius is preserved also between knots.
_cool=next(i for i,row in enumerate(TRACK) if row["phase"]=="白矮星")
_cool_radius=.5*_lum[_cool:]+2*(np.log(TSUN)-_temp[_cool:])
_r_slope=PchipInterpolator(TIMES[_cool:],_cool_radius).derivative()(TIMES[_cool:])
_slopes[_cool:]=4*_temperature.derivative()(TIMES[_cool:])+2*_r_slope
_luminosity=CubicHermiteSpline(TIMES,_lum,_slopes)

def evolved(t):
    t=min(TIMES[-1],max(TIMES[0],t))
    i=bisect_right(TIMES,t)-1
    return Star(TRACK[i]["phase"],float(np.exp(_temperature(t))),float(np.exp(_luminosity(t))),
                min(1,max(0,(t-225)/50)))

SUN = Star("太阳基准",5772,1)
GIANT = evolved(175)
DWARF = evolved(285)

def state_at(event, t):
    if event in ("giants","giant_photo","recap1"): return GIANT
    if event in ("dwarfs","dwarf_photo","recap2"): return DWARF
    if event == "mainband": return Star("主序星示例",10500,36)
    if event == "compare": return Star("主序星示例",3750,0.048)
    return SUN if t < TIMES[0] else evolved(t)

