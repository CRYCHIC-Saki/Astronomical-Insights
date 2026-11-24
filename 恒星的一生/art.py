"""Shared Manim atlas, stellar textures and screen-space type. Design canvas: 1920×1080."""
from functools import lru_cache
from pathlib import Path
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from manim import Camera, Line, VGroup, Text, Rectangle, config
from physics import *

BG="#0B1420"
PANEL="#142333"
GRID="#344353"
INK="#F4F0E6"
MUTED="#ABC0CB"
GOLD="#F2C98B"
MINT="#83D8CA"
FONTDIR=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"
TEMPS=[2500,3500,4800,5772,7800,20000,120000]
COLORS=np.array([[226,101,58],[249,155,92],[255,213,167],[255,242,218],[235,242,255],[183,210,255],[156,191,246]])
def star_color(temp):
    return tuple(int(np.interp(np.log(temp),np.log(TEMPS),COLORS[:,i])) for i in range(3))

def uv(t,l):
    x,y=hr_to_point(t,l)
    return (x-LEFT)/(RIGHT-LEFT),(y-TOP)/(BOTTOM-TOP)

def populations():
    rng=np.random.default_rng(5772)
    result=[]
    for group,count in [("mainband",60),("giants",18),("dwarfs",18)]:
        i=0
        while i<count:
            if group=="mainband":
                t=10**rng.uniform(math.log10(2850),math.log10(36200))
                l=(t/TSUN)**(8.7 if t<TSUN else 6.4)*10**rng.normal(0,.2)
            elif group=="giants":
                t=rng.uniform(3020,5100)
                l=10**(1.35+2.15*(5100-t)/2080+rng.normal(0,.31))
            else:
                t=10**rng.uniform(3.82,4.59)
                l=.013**2*(t/TSUN)**4*10**rng.normal(0,.2)
            if LMIN<l<LMAX:
                result.append((group,*uv(t,l),rng.uniform(.76,1)))
                i+=1
    rng.shuffle(result)
    return result
POP=populations()
XTICKS=(100000,30000,10000,5772,3000)
YTICKS=(10000,100,1,.01,.0001)

@lru_cache(None)
def atlas():
    """Rasterize the Manim grid once. The crop used for this plate also maps every overlay."""
    w,h=1600,880
    def pt(u,v):return np.array([(u-.5)*16,(.5-v)*8.8,0])
    grid=VGroup()
    for t in XTICKS:
        u,_=uv(t,1)
        grid.add(Line(pt(u,0),pt(u,1),stroke_color=GRID,stroke_width=1))
    for l in YTICKS:
        _,v=uv(TSUN,l)
        grid.add(Line(pt(0,v),pt(1,v),stroke_color=GRID,stroke_width=1))
    cam=Camera(pixel_width=w,pixel_height=h,frame_width=16,frame_height=8.8,background_color="#0E1A28")
    cam.capture_mobjects([grid])
    return cam.get_image().convert("RGB")

@lru_cache(None)
def band():
    rgb=[star_color(TMAX*(TMIN/TMAX)**(i/999)) for i in range(1000)]
    return Image.fromarray(np.array([rgb],dtype=np.uint8))

@lru_cache(None)
def background(w,h):
    yy,xx=np.mgrid[:h,:w]
    halo=np.exp(-((xx/w-.69)**2/.23+(yy/h-.39)**2/.19))
    rgb=np.array([9,17,27])+halo[:,:,None]*[7,10,14]
    im=Image.fromarray(rgb.astype("uint8"))
    d=ImageDraw.Draw(im)
    rng=np.random.default_rng(814)
    for x,y in rng.uniform([.035,.08],[.966,.79],(58,2)):
        col="#475A67" if rng.random()<.65 else "#31434F"
        rad=max(1,round(w/1920))
        px,py=int(x*w),int(y*h)
        d.ellipse((px,py,px+rad,py+rad),fill=col)
    return im

@lru_cache(None)
def stellar_maps():
    n=768
    y,x=np.mgrid[:n,:n]
    r=np.hypot(x-(n-1)/2,y-(n-1)/2)/(n*.36)
    mu=np.sqrt(np.maximum(0,1-r*r))
    rng=np.random.default_rng(1904)
    grain=np.zeros_like(r)
    for size,amp in [(17,.035),(63,.060),(175,.036)]:
        noise=Image.fromarray(rng.integers(0,256,(size,size),dtype=np.uint8)).resize((n,n),Image.Resampling.BICUBIC)
        grain+=amp*(np.asarray(noise)/127.5-1)
    shade=np.clip(.63+.34*mu+grain,0,1)
    shade[r>1]=.86
    alpha=np.where(r<1,255,np.exp(-11*np.maximum(0,r-1))*58)*np.clip((1.38-r)*14,0,1)
    return Image.fromarray((255*shade).astype("uint8")), Image.fromarray(alpha.astype("uint8"))

@lru_cache(24)
def colored_star(rgb,quiet):
    shade,alpha=stellar_maps()
    if quiet: rgb=tuple(round(c*.70) for c in rgb)
    disk=ImageOps.colorize(shade,(0,0,0),rgb)
    disk.putalpha(alpha.point(lambda a:a if a>200 else round(a*.14)) if quiet else alpha)
    return disk

@lru_cache(64)
def disk(rgb,quiet,size):
    return colored_star(rgb,quiet).resize((size,size),Image.Resampling.BILINEAR)

@lru_cache(None)
def gas_texture():
    n=640
    y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]
    th=np.arctan2(y,x)
    rho=np.hypot(x,y*1.13)
    center=.72+.075*np.cos(2*th)+.036*np.sin(3*th)+.022*np.sin(5*th)
    k=rho-center
    filaments=np.exp(-(k/.051)**2)+.54*np.exp(-((k+.072)/.019)**2)
    strength=filaments*(.45+.55*np.sin(th*2-.8)**2)*(.7+.3*np.sin(th*14+rho*37)**2)
    rgb=np.empty((n,n,4),dtype=np.uint8)
    warm=(np.sin(th*2+1)+1)/2
    for i,(a,b) in enumerate(zip((98,192,187),(231,158,127))):
        rgb[:,:,i]=a+(b-a)*warm
    rgb[:,:,3]=np.clip(strength*183,0,235)
    return Image.fromarray(rgb)

@lru_cache(512)
def glyph(txt,px,color,face="sans"):
    fn={"sans":"msyh.ttc","serif":"simsun.ttc","mono":"consola.ttf","math":"cambria.ttc"}[face]
    f=font(fn,px)
    a,b,c,d=f.getbbox(txt)
    im=Image.new("RGBA",(max(1,c-a+4),max(1,d-b+4)))
    ImageDraw.Draw(im).text((2-a,2-b),txt,font=f,fill=color)
    return im

@lru_cache(120)
def font(name,px):
    return ImageFont.truetype(str(FONTDIR/name),max(8,px))

@lru_cache(None)
def wires(density):
    n=96
    lon=np.linspace(-math.pi,math.pi,n+1)
    lat=np.linspace(-math.pi/2,math.pi/2,n+1)
    curves=[(np.full_like(lat,a),lat) for a in np.linspace(-math.pi,math.pi,12*density,endpoint=False)]
    curves += [(lon,np.full_like(lon,b)) for b in np.linspace(-math.pi/2,math.pi/2,6*density+1)[1:-1]]
    result=[]
    for a,b in curves:
        x,y,z=np.cos(b)*np.sin(a),np.sin(b),np.cos(b)*np.cos(a)
        idx=np.flatnonzero(.286*y+.958*z>=0)
        pts=np.column_stack((x,.286*z-.958*y))
        for section in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
            if len(section)>1:result.append(pts[section])
    return result

