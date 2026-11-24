"""Independent shot framing on the storyboard clock. hr field of view is in log-chart UV."""
from typing import NamedTuple
import numpy as np
from manim.utils.rate_functions import smootherstep
from scipy.interpolate import PchipInterpolator
from physics import TIMES

def ease(x):
    return float(smootherstep(min(1,max(0,x))))

def ramp(t,a,b):
    return ease((t-a)/(b-a))

def mix(a,b,p):return a+(b-a)*p

class View(NamedTuple):
    x:float; y:float; w:float; h:float
    zoom:float; focus_x:float; focus_y:float
    sx:float; sy:float; lens:float; visibility:float

FULL=View(190,180,1520,565,1,.5,.5,1640,420,1.12,1)
REGION=View(170,194,1160,540,1,.5,.5,1605,445,1.12,1)
PAIR=View(145,228,944,474,1,.5,.5,1500,446,1.23,1)
TEMP_VIEW=View(155,229,1070,467,1.65,.80,.43,1550,454,1.12,1)
HERO=View(110,586,500,216,1,.5,.5,1235,450,1.68,1)
EXPERIMENT=HERO._replace(x=70,y=680,w=350,h=145,sx=1235,sy=450,visibility=0)
CLOSE=HERO._replace(sx=1225,sy=440,lens=1.78)
LOCAL=REGION._replace(zoom=3.1,focus_x=.79,focus_y=.55)
INTRO_VIEW=FULL._replace(zoom=1.15,focus_x=.73,visibility=0)

# Each target is fixed in chart coordinates. No camera tracks a moving data point.
KEYS=[
    (25,3,INTRO_VIEW._replace(visibility=1)),(55,3,FULL),
    (76,2.2,REGION._replace(zoom=1.28,focus_x=.66,focus_y=.43)),
    (88,2.6,REGION._replace(zoom=2.25,focus_x=.91,focus_y=.24)),
    (97,2.7,REGION._replace(zoom=2.05,focus_x=.50,focus_y=.73)),
    (105,2.5,REGION),(113,2.5,LOCAL),(128,2.7,PAIR),
    (137,2.6,TEMP_VIEW),(153.15,1.5,HERO),(158,2,EXPERIMENT),(180,2.3,HERO),
    (189,1.2,PAIR),(204,2.6,CLOSE),(231,2.6,PAIR),(245,2,REGION),
    (259,2.5,HERO._replace(visibility=0,sx=1210,sy=445)),
    (287,2.5,REGION),(301,2.5,FULL)]
def camera(t):
    old=INTRO_VIEW
    for start,duration,target in KEYS:
        if t<start:break
        if t<start+duration:
            p=ramp(t,start,start+duration)
            return View(*(mix(a,b,p) for a,b in zip(old,target)))
        old=target
    return old

def window(v):
    span=1/v.zoom
    left=min(1-span,max(0,v.focus_x-span/2))
    top=min(1-span,max(0,v.focus_y-span/2))
    return left,top,span

def project(v,u,b):
    l,t,span=window(v)
    return v.x+(u-l)*v.w/span,v.y+(b-t)*v.h/span

class StateClock:
    def __init__(self,cues):
        anchors=[c for c in cues if c.event in {"follow","hydrogen","state","leave","expand","area","adjust","shed","core","hotcore","fade","small","example","cool","recap1"}]
        times=[c.start for c in anchors]
        values=[c.anchor for c in anchors]
        # Arrive before the cut, leaving both projected temperatures on screen.
        reading=next(c for c in anchors if c.event=="expand")
        arrival=next(c for c in anchors if c.event=="area")
        i=times.index(reading.start)+1
        settle=min(reading.end-.35,max(reading.start+1.4,reading.phrases[-1][0]))
        times[i:i]=[reading.start+.65, settle]
        values[i:i]=[reading.anchor, arrival.anchor]
        fade=next(c for c in anchors if c.event=="fade")
        i=times.index(fade.start)
        times.insert(i,fade.start-.5)
        values.insert(i,fade.anchor)
        self.clock=PchipInterpolator(times,values)
        self.start,self.end=times[0],times[-1]

    def __call__(self,t):
        return float(self.clock(np.clip(t,self.start,self.end)))

