"""Visual derivation of bolometric luminosity. Coordinates use the film's design canvas."""
import math
import re
from functools import lru_cache

from PIL import Image, ImageOps

from art import BG, GOLD, GRID, INK, MINT, MUTED, colored_star, display_radius, font, star_color
from camera_track import mix, ramp
from physics import SUN, TSUN

AREA_X, FLUX_X = 560, 1350
QUANTITATIVE = {"windows", "surface", "product", "ratio", "flux_calc", "area_calc", "law", "example"}


@lru_cache(256)
def math_parts(expression, size):
    # Subscripts and superscripts keep their actual baseline even at preview resolution.
    parts = []
    advance = 0
    subscript_left = None
    for token in re.split(r"([_^]\{[^{}]+\})", expression):
        if not token:
            continue
        if token.startswith(("_{", "^{")):
            raised = token[0] == "^"
            txt, px, dy = token[2:-1], round(size*.56), size*(-.41 if raised else .31)
        else:
            txt, px, dy = token, size, 0
        width = font("cambria.ttc", px).getlength(txt)
        left = subscript_left if token.startswith("^{") and subscript_left is not None else advance
        subscript_left = left if token.startswith("_{") else None
        parts.append((txt, px, dy, left))
        advance = max(advance, left+width)
    return advance, parts


def equation(c, x, y, expression, size=58, color=INK, opacity=1):
    if opacity <= 0:
        return
    width, parts = math_parts(expression, size)
    start = x-width/2
    for txt, px, dy, left in parts:
        # glyph() trims bearings and leading spaces; center each measured chunk.
        core = txt.strip()
        if core:
            normal = font("cambria.ttc", px)
            pad = normal.getlength(txt[:len(txt)-len(txt.lstrip())])
            c.text(start+left+pad+normal.getlength(core)/2, y+dy, core, px, color, "center", opacity, "math")


def rounded_significant(value, digits):
    return round(value, digits-1-math.floor(math.log10(value)))


def numbers(star):
    # All teaching approximations derive from the displayed star; never interpolate R separately.
    area = star.radius**2
    flux = (star.temperature/TSUN)**4
    return area, flux, area*flux


@lru_cache(12)
def window_patch(temperature, size):
    disk = colored_star(star_color(temperature), False)
    cx, cy = disk.width//2, disk.height//2
    thumb = disk.crop((cx-65, cy-65, cx+65, cy+65)).convert("RGB")
    thumb = thumb.resize((size, size), Image.Resampling.BILINEAR)
    return ImageOps.expand(thumb, border=max(1,size//55), fill=MINT).convert("RGBA")


def patch_and_leader(c, cx, cy, radius, px, py, star, size, progress=1):
    # The leader identifies a surface location. The inset alone denotes a fixed physical area.
    origin = (cx+radius*.49, cy-radius*.32)
    target = (mix(origin[0],px,progress), mix(origin[1],py,progress))
    c.line([origin, target], MINT, 2)
    c.circle(*origin, 4, MINT)
    side = max(2, round(size*c.s*progress))
    if progress > .015:
        c.sprite(*target, window_patch(round(star.temperature),side), progress)


def bar(c, x, y, width, fraction, color=MINT):
    c.line([(x,y),(x+width,y)], GRID, 15)
    if fraction > 0:
        c.line([(x,y),(x+width*min(1,fraction),y)],color,15)


def surface_pair(c, star, event, q, now):
    dt, duration = now-q.start, q.end-q.start
    _, flux, _ = numbers(star)
    c.text(960,100,"相同面积，示意",43,INK,"center")
    p = ramp(dt,.15,1.65) if event=="windows" else 1
    power = ramp(dt,.35,1.6) if event=="surface" else 0
    for x, obj, label in [(AREA_X,SUN,"太阳"),(FLUX_X,star,"红巨星")]:
        radius = display_radius(obj.radius)*.91
        c.star(x-75,413,obj,radius)
        patch_and_leader(c,x-75,413,radius,x+120,366,obj,112,p)
        c.text(x,595,label,36,INK,"center")
        if power:
            value = 1 if obj is SUN else flux
            bar(c,x-145,663,290,value*power)
    if event=="windows":
        c.text(960,730,"每个窗口  1 m²",34,MINT,"center",ramp(dt,1.6,2.6))
    elif event=="surface":
        equation(c,960,212,"F_{surf} = σ T_{eff}^{4}",65,MINT,power)
        c.text(960,754,"单位面积辐射功率（全波段，W/m²）",35,MINT,"center",power)
        legend=ramp(dt,duration*.48,duration*.62)
        c.text(752,820,"有效表面温度",28,MUTED,"center",legend)
        equation(c,930,820,"T_{eff} (K)",32,MUTED,legend)
        c.text(1133,820,"σ 为常数",28,MUTED,"center",legend)


def product(c, star, q, now):
    dt = now-q.start
    c.text(960,104,"从一平方米到整个球面",44,INK,"center")
    c.star(AREA_X,420,star,120)
    c.radius(AREA_X,420,120)
    patch_and_leader(c,AREA_X,420,120,FLUX_X,420,star,116)
    c.text(AREA_X,610,"球面面积",33,GOLD,"center")
    c.text(FLUX_X,610,"每平方米辐射功率",33,MINT,"center")
    move = ramp(dt,.3,2.5)
    y = mix(688,217,move)
    equation(c, mix(AREA_X,865,move),y,"4πR^{2}",60,GOLD)
    if move>.01:
        equation(c,637,217,"L =",61,INK,move)
        equation(c,1010,217,"×",58,INK,move)
    replace = ramp(dt, q.phrases[-1][0]-q.start, q.phrases[-1][0]-q.start+1.15)
    x = mix(FLUX_X,1184,move)
    equation(c,x,y,"F_{surf}",61,MINT,1-replace)
    equation(c,x,y,"σ T_{eff}^{4}",61,MINT,replace)


def ratio_header(c, star, dwarf, substitute):
    title = "白矮星 · 冷却途中的一个状态" if dwarf else "红巨星 · 以太阳为基准"
    c.text(960,90,title,41,INK,"center",face="serif")
    general=[("L/L_{⊙} = ", INK), ("(R/R_{⊙})^{2}", GOLD), (" × ", INK), ("(T_{eff}/T_{⊙})^{4}", MINT)]
    numeric=[general[0], (f"({star.radius:.3f})^{{2}}",GOLD), general[2],
             (f"({star.temperature:.0f}/{TSUN})^{{4}}",MINT)]
    for row,alpha in [(general,1-substitute),(numeric,substitute)]:
        if alpha<=0:continue
        widths=[math_parts(term,55)[0] for term,_ in row]
        left=960-sum(widths)/2
        for (term,color),width in zip(row,widths):
            equation(c,left+width/2,199,term,55,color,alpha)
            left+=width


def factor_images(c, star, dwarf, area_ready, flux_ready, bar_progress, show_flux):
    area, flux, _ = numbers(star)
    radius = star.radius
    # A physically scaled inset is kept distinct from the magnified dwarf disk.
    if dwarf:
        c.circle(AREA_X-85,420,72,None,MUTED,2)
        c.circle(AREA_X-85,420,max(1,72*radius),MINT)
        c.line([(AREA_X-81,420),(AREA_X+24,398)],MUTED,2)
        c.circle(AREA_X+68,398,42,None,MUTED,2)
        c.star(AREA_X+68,398,star,28)
        c.text(AREA_X+68,469,"局部放大",23,MUTED,"center")
    else:
        r = display_radius(radius)*.73
        c.star(AREA_X,418,star,r)
        c.radius(AREA_X,418,r)
    c.text(AREA_X,285,"球面面积",33,GOLD,"center")
    c.text(FLUX_X,285,"每平方米辐射功率",33,MINT,"center")
    c.sprite(FLUX_X-164,415,window_patch(round(star.temperature),max(10,round(88*c.s))))
    x, width = FLUX_X-67, 270
    if show_flux:
        reference = 1/max(1,flux)
        c.text(x,368,"太阳  1",24,MUTED)
        bar(c,x,395,width,reference,MUTED)
        bar(c,x,461,width,mix(reference,flux/max(1,flux),bar_progress))
        c.text(x,503,"本例",24,MUTED)
    if area_ready:
        equation(c,AREA_X,564,f"R ≈ {radius:.3g} R_{{⊙}}",40,GOLD,area_ready)
    if flux_ready:
        equation(c,FLUX_X,564,f"{star.temperature:.0f} K",43,MINT,flux_ready)


def calculation(c, star, event, q, now):
    dt = now-q.start
    dwarf = event=="example"
    area, flux, luminosity = numbers(star)
    ratio_header(c,star,dwarf,ramp(dt,3,4.2) if dwarf else 0)
    if dwarf:
        # Each calculation starts at its recorded phrase onset.
        anchors=[p[0]-q.start for p in q.phrases[1:]]
        area_on,flux_on,product_on = anchors if len(anchors)==3 else [(q.end-q.start)*p for p in (.2,.48,.72)]
        area_in = ramp(dt,area_on,area_on+1.15)
        flux_in = ramp(dt,flux_on,flux_on+1.15)
        area_out = ramp(dt,area_on+1.65,area_on+2.45)
        flux_out = ramp(dt,flux_on+1.45,flux_on+2.35)
        merge = ramp(dt,product_on,product_on+1.35)
        ar = f"{area:.6f}"
        fl = f"{flux:.0f}"
        radius_text = f"({star.radius:.3f})^{{2}}"
    else:
        ar = f"{rounded_significant(area,2):.0f}"
        fl = f"{flux:.3f}"
        radius_text = f"{star.radius:.0f}^{{2}} = {round(star.radius)**2}"
        area_in = 1 if event=="law" else (ramp(dt,.2,1.3) if event=="area_calc" else 0)
        flux_in = ramp(dt,.2,1.3) if event=="flux_calc" else float(event in {"area_calc","law"})
        area_out = 1 if event=="law" else (ramp(dt,3,4.35) if event=="area_calc" else 0)
        flux_out = ramp(dt,3.0,4.4) if event=="flux_calc" else float(event in {"area_calc","law"})
        merge = ramp(dt,.35,1.85) if event=="law" else 0
    area_ready = area_in if not dwarf else ramp(dt,.15,1.15)
    flux_ready = flux_in if not dwarf else ramp(dt,.15,1.15)
    factor_images(c,star,dwarf,area_ready,flux_ready,flux_out,flux_in>0)
    x_area,x_flux = mix(AREA_X,601,merge),mix(FLUX_X,972,merge)
    y = mix(701,722,merge)
    equation(c,AREA_X,mix(590,701,area_in),radius_text,49,GOLD,area_in*(1-area_out))
    equation(c,x_area,y,("≈ " if merge<.02 else "")+ar,64,GOLD,area_out)
    temp_expression = f"({star.temperature:.0f}/{TSUN})^{{4}}"
    equation(c,FLUX_X,mix(590,701,flux_in),temp_expression,48,MINT,flux_in*(1-flux_out))
    equation(c,x_flux,y,("≈ " if merge<.02 else "")+fl,64,MINT,flux_out)
    if event=="ratio":
        equation(c,960,715,f"T_{{⊙}} = {TSUN} K",43,MUTED,ramp(dt,.7,1.7))
    if merge:
        equation(c,809,722,"×",55,INK,merge)
        equation(c,1150,722,"≈",55,INK,merge)
        value=f"{luminosity:.3f}" if dwarf else f"{luminosity:.0f}"
        equation(c,1340,722,value,71,INK,merge)
        c.text(1340,803,"太阳光度",30,MUTED,"center",merge)

