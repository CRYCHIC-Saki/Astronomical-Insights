"""Cinematic Manim CE scene. The master and sample use the same camera and state clock."""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from PIL.ImageColor import getrgb
from manim import Camera, Scene, ValueTracker, config, linear
import luminosity as lesson
from art import *
from camera_track import camera, project, window, ease, ramp, mix, StateClock
from timing import prepare

def opacity(image,a):
    if a>=.999:return image.getchannel("A")
    return image.getchannel("A").point(lambda v:round(v*a))

class Canvas:
    def __init__(self,im):
        self.im=im
        self.s=im.width/1920
        self.draw=ImageDraw.Draw(im)
    def coord(self,x,y):return round(x*self.s),round(y*self.s)
    def line(self,points,color,width=2):
        if len(points)>1:
            self.draw.line([self.coord(*p) for p in points],fill=color,width=max(1,round(width*self.s)),joint="curve")
    def circle(self,x,y,r,color=None,edge=None,width=2):
        self.draw.ellipse([self.coord(x-r,y-r),self.coord(x+r,y+r)],fill=color,outline=edge,width=max(1,round(width*self.s)))
    def text(self,x,y,txt,size=32,color=INK,align="left",a=1,face="sans"):
        if not txt or a<=0:return
        ink=glyph(txt,max(9,round(size*self.s)),color,face)
        px,py=self.coord(x,y)
        px-=round(ink.width*{"left":0,"center":.5,"right":1}[align])
        self.im.paste(ink,(px,py-ink.height//2),opacity(ink,a))
    def sprite(self,x,y,image,a=1):
        px,py=self.coord(x,y)
        self.im.paste(image,(px-image.width//2,py-image.height//2),opacity(image,a))
    def star(self,x,y,st,r,a=1):
        if a<=0 or r<1:return
        side=max(3,round(2*r*self.s/.72))
        dim=1-.30*(1-ramp(st.radius,.015,.065))
        color=tuple(round(k*dim) for k in star_color(st.temperature))
        self.sprite(x,y,disk(color,False,side),a)
    def dashed(self,x,y,end,color):
        for pos in np.arange(x,end,19):self.line([(pos,y),(min(pos+11,end),y)],color,2)
    def radius(self,x,y,r):
        self.line([(x,y),(x+r,y)],BG,4)
        self.line([(x+r,y-8),(x+r,y+8)],MINT,3)
        self.circle(x,y,4,BG)

def accent(c,x,y,title,value=None,a=1):
    c.text(x,y,title,34,MUTED,a=a)
    if value:c.text(x,y+68,value,59,GOLD,a=a,face="serif")

def in_view(v,x,y):return v.x<=x<=v.x+v.w and v.y<=y<=v.y+v.h

@lru_cache(3)
def chart_base(w,h,v,pop,group,axes,population_progress,band_progress,highlight,dim):
    base=background(w,h)
    if v.visibility<=0:return base
    im=base.copy()
    c=Canvas(im)
    l,t,d=window(v)
    detail=ramp(v.w,598,775)
    ax,ay=c.coord(v.x,v.y)
    aw,ah=c.coord(v.w,v.h)
    if axes>0:
        tile=atlas()
        box=tuple(max(0,min(dim,offset*dim)) for offset,dim in [(l,tile.width),(t,tile.height),(l+d,tile.width),(t+d,tile.height)])
        tile=tile.resize((aw,ah),Image.Resampling.BILINEAR,box=box)
        if axes<1:tile=Image.blend(im.crop((ax,ay,ax+aw,ay+ah)),tile,axes)
        im.paste(tile,(ax,ay))
    if band_progress>0:
        length=max(1,round(aw*band_progress))
        col=band().resize((aw,max(2,round(c.s*5))),Image.Resampling.BILINEAR,
                          box=(1000*l,0,min(1000,1000*(l+d)),1))
        im.paste(col.crop((0,0,length,col.height)),(ax,ay+ah))
    if detail>0:
        for num in XTICKS:
            x,_=project(v,*uv(num,1))
            if v.x-1<=x<=v.x+v.w*band_progress+1:c.text(x,v.y+v.h+25,f"{num:,}",25,MUTED,"center",detail)
        if axes>.1:
            for num in YTICKS:
                _,y=project(v,*uv(TSUN,num))
                if v.y<=y<=v.y+v.h:c.text(v.x-14,y,f"{num:g}",24,MUTED,"right",axes*detail)
            c.text(v.x,v.y-32,"光度  /  L⊙",27,MUTED,a=axes*detail)
        c.text(v.x+v.w/2,v.y+v.h+68,"表面温度  /  K",28,MUTED,"center",band_progress*detail)
    if detail<1:
        c.text(v.x,v.y-28,"赫罗图",25,MUTED,a=1-detail)
        c.text(v.x,v.y+v.h+22,"热",21,MUTED,a=1-detail)
        c.text(v.x+v.w,v.y+v.h+22,"冷",21,MUTED,"right",1-detail)
    if pop:
        draw=ImageDraw.Draw(im,"RGBA")
        region_color={"mainband":(176,208,205),"giants":(248,178,123),"dwarfs":(168,197,236)}
        for i,(g,u,b,weight) in enumerate(POP):
            x,y=project(v,u,b)
            if not in_view(v,x,y):continue
            fade=ease((population_progress*1.17-i/len(POP))/.17) if population_progress<1 else 1
            target=.9 if g==group else .13
            power=mix(.44,target,highlight) if group else .44
            power=mix(power,.21,dim)
            r=max(1,round(mix(2.4,4,detail)*c.s))
            X,Y=c.coord(x,y)
            draw.ellipse((X-r,Y-r,X+r,Y+r),fill=(*region_color[g],round(255*power*weight*fade)))
    return Image.blend(base,im,v.visibility) if v.visibility<1 else im

PATH_TIMES=np.unique(np.r_[np.arange(124,310,.40),TIMES])
PATH_UV=np.array([uv(evolved(t).temperature,evolved(t).luminosity) for t in PATH_TIMES])
EXAMPLES={"mainband":(Star("主序星",10500,36),"主序带"),"giants":(GIANT,"红巨星区"),"dwarfs":(DWARF,"白矮星区")}
def trail(c,v,t,star):
    l,top,span=window(v)
    pts=PATH_UV[:np.searchsorted(PATH_TIMES,t)]
    pts=np.vstack((pts,uv(star.temperature,star.luminosity)))
    screen=(pts-[l,top])*[v.w/span,v.h/span]+[v.x,v.y]
    ok=(screen[:,0]>=v.x)&(screen[:,0]<=v.x+v.w)&(screen[:,1]>=v.y)&(screen[:,1]<=v.y+v.h)
    ids=np.flatnonzero(ok)
    for run in np.split(ids,np.flatnonzero(np.diff(ids)>1)+1):
        color=tuple(round(mix(b,g,v.visibility)) for b,g in zip(getrgb(BG),getrgb(GOLD)))
        if len(run)>1:c.line(screen[run],color,2.7)
def marker(c,v,star,a=1):
    x,y=project(v,*uv(star.temperature,star.luminosity))
    if in_view(v,x,y) and a>.005:
        r=mix(7,12,ramp(v.w,590,790))*a
        c.circle(x,y,r,None,GOLD,2.5)
        c.circle(x,y,4*a,GOLD)
    return x,y

class Shot:
    def __init__(self,cue,w,h,clock):
        self.c=cue
        self.w,self.h=w,h
        self.clock=clock
        self.tracker=ValueTracker(cue.plan)

    def frame(self,actual):
        q=self.c
        event=q.event
        elapsed=actual-q.start
        u=min(1,max(0,elapsed/(q.end-q.start)))
        t=mix(q.plan,q.next_plan,u)
        self.tracker.set_value(t)
        v=camera(self.tracker.get_value())
        axes=ramp(t,47,49.2)
        pop=2 if t>=113 else int(t>=69)
        group=event if event in EXAMPLES else ""
        highlight=ramp(u,0,.13)*(1-ramp(u,.87,1)) if group else 0
        base=chart_base(self.w,self.h,v,pop,group,axes,ramp(t,69,73),ramp(t,25.5,31),
                        highlight,ramp(t,113,114.5))
        c=Canvas(base.copy())
        state_t=self.clock(actual)
        if t>=301:state_t=TIMES[-1]
        st=evolved(state_t)
        if t<113:st=EXAMPLES[event][0] if event in EXAMPLES else SUN
        if t<32:self.opening(c,t,v)
        elif t<69:self.axes(c,t,v,event)
        elif t<113:self.regions(c,t,v,event,st,u)
        elif event in lesson.QUANTITATIVE:
            c=self.quantitative(c,t,v,st,state_t,actual)
        else:self.evolution(c,t,v,event,st,state_t,actual)
        c.line([(92,931),(1828,931)],"#293846",1.5)
        c.text(98,884,"时间非等比 · 尺寸非比例 · 点大小不代表半径",23,MUTED)
        caption=q.caption(actual)
        if caption:c.text(960,1006,caption,39,INK,"center")
        return c.im

    def opening(self,c,t,v):
        # The three independent examples share a symbol size; the Sun alone demonstrates projection.
        to_chart=ramp(t,25.4,31)
        choose=ramp(t,21.3,25.3)
        x,y=project(v,*uv(SUN.temperature,SUN.luminosity))
        for px,py,example in [(525,360,Star("蓝白示例",18000,60)),(1390,466,Star("橙红示例",3500,12))]:
            c.star(px,py,example,32,1-choose)
        radius=mix(mix(32,90,choose),6,to_chart)
        c.star(mix(895,x,to_chart),mix(635,y,to_chart),SUN,radius)
        question=ramp(t,8,9.3)*(1-ramp(t,17,18.5))
        c.text(960,169,"更热，就更亮？",77,INK,"center",question,"serif")
        c.text(960,174,"光度",55,INK,"center",ramp(t,17.4,18.7)*(1-ramp(t,22,23.2)),"serif")
        c.text(895,777,"太阳",32,GOLD,"center",choose*(1-ramp(t,25.4,28)))
        if to_chart>.8:marker(c,v,SUN,ramp(t,29.3,31))

    def quantitative(self,c,t,v,st,state_t,actual):
        q=self.c
        e=q.event
        elapsed=actual-q.start
        remaining=q.end-actual
        plate=Canvas(background(self.w,self.h).copy())
        if e in {"windows","surface"}:
            lesson.surface_pair(plate,st,e,q,actual)
        elif e=="product":
            lesson.product(plate,st,q,actual)
        else:
            lesson.calculation(plate,st,e,q,actual)
        alpha=1
        if e in {"windows","example","ratio"}:
            alpha=ramp(elapsed,0,.85)
        if e=="product":
            alpha=ramp(remaining,0,.75)
        if e=="law":
            alpha=ramp(remaining,1.4,3.15)
        if e=="example":
            alpha=min(alpha,ramp(remaining,0,1.2))
        if alpha<1:
            self.evolution(c,t,v,e,st,state_t,actual)
            if e=="law":
                x,y=project(v,*uv(st.temperature,st.luminosity))
                c.dashed(v.x,y,x,GOLD)
                c.text(v.x+15,y-40,f"约 {st.luminosity:.0f} L⊙",34,GOLD)
            return Canvas(Image.blend(c.im,plate.im,alpha))
        return plate

    def axes(self,c,t,v,event):
        x,y=project(v,*uv(TSUN,1))
        bottom=v.y+v.h
        if t>=40:
            amount=ramp(t,40.4,45)
            c.line([(x,bottom),(x,mix(bottom,y,amount))],MINT,3)
        if t>=54:
            amount=ramp(t,54.3,58.2)
            c.dashed(v.x,y,mix(v.x,x,amount),GOLD)
        marker(c,v,SUN)
        if event=="hot":
            f=ramp(t,33,38.4)
            tip=mix(v.x+32,x,f)
            c.circle(tip,bottom,7,GOLD)
            c.text(tip,bottom-40,"左热 · 右冷" if f<.96 else "5772 K",32,GOLD,"center")
        if event in {"lum","project_l"}:c.text(x+30,y-27,"太阳",28,GOLD)
        if event=="distance":
            f=ramp(t,62.6,66.2)
            a=ramp(t,61,61.8)*(1-ramp(t,68.2,69))
            c.star(490,384,SUN,mix(85,31,f),(1-.45*f)*a)
            c.text(490,526,"远处所见",29,MUTED,"center",a)
    def regions(self,c,t,v,event,st,u):
        if event=="population":
            marker(c,v,SUN)
            c.text(v.x+v.w,v.y-34,"恒星分布示意",27,MUTED,"right")
        elif event in EXAMPLES:
            a=ramp(u,0,.13)*(1-ramp(u,.87,1))
            marker(c,v,st,a)
            c.star(v.sx,v.sy,st,display_radius(st.radius)*v.lens,a)
            c.text(v.sx,698,EXAMPLES[event][1],41,INK,"center",a,"serif")
        else:
            for obj,title,d in [(Star("",13000,120),"较大质量",0),(Star("",3750,.048),"较小质量",.17)]:
                a=ramp(u,d,d+.22)*(1-ramp(u,.90,1))
                x,y=marker(c,v,obj,a)
                c.text(x-22,y-28,title,26,INK,"right",a)
    def evolution(self,c,t,v,e,st,state_t,actual):
        experiment=ramp(t,158,160)*(1-ramp(t,180,182.3))
        scale_scene=ramp(t,259,261.5)*(1-ramp(t,287,289.5))
        star_visibility=1-ramp(t,301,303.5)
        if v.visibility>.005:
            trail(c,v,state_t,st)
            marker(c,v,st,v.visibility)
        r=display_radius(st.radius)*v.lens
        sx,sy=v.sx,v.sy
        if e in {"hotcore","fade"} and t<246:
            _,y=project(v,*uv(100000,2200))
            c.dashed(v.x,y,v.x+v.w,"#588780")
        if 204<=t<259:
            gas=st.gas_progress
            size=max(2,round((display_radius(evolved(225).radius)*2.85+gas*235)*v.lens*c.s))
            alpha=ramp(gas,0,.14)*(1-ramp(gas,.46,1))
            if alpha>.002:c.sprite(sx,sy,gas_texture().resize((size,size),Image.Resampling.BILINEAR),alpha)
        big=105*(1+ramp(t,163.2,168.8))
        radius=mix(r,big,experiment)
        radius=mix(radius,44,scale_scene)
        c.star(sx,sy,st,radius,star_visibility)
        if 134<=t<152:
            ref=display_radius(SUN.radius)*v.lens
            if r>ref+1:
                box=[c.coord(sx-ref,sy-ref),c.coord(sx+ref,sy+ref)]
                for angle in range(0,360,24):
                    c.draw.arc(box,angle,angle+14,fill="#6A5845",width=max(1,round(c.s*3)))
                g=ref*.7071
                c.line([(sx-g,sy+g),(sx-r-32,sy+r*.72)],MINT,2)
                c.text(sx-r-42,sy+r*.72,"原表面",26,MUTED,"right")
        if experiment>.001:
            self.experiment(c,t,st,sx,sy,big,experiment)
        if scale_scene>.001:self.dwarf_scale(c,t,st,v,scale_scene)
        self.notes(c,t,v,e,st,actual)
        if e=="area" and t>153.65:c.radius(sx,sy,r)
        if e=="core":
            c.radius(sx,sy,r)
            c.text(sx+r+20,sy-24,"中心星",29,MINT)
    def experiment(self,c,t,st,sx,sy,big,a):
        c.star(660,sy,st,105,a)
        c.text(960,162,"同温球面",53,INK,"center",a,"serif")
        c.text(960,231,"本镜头半径按比例",27,MUTED,"center",a)
        right_label="2R" if big>209.8 else ("R" if big<105.2 else "")
        for x,r,txt in [(660,105,"R"),(sx,big,right_label)]:
            if a>.04:
                color=tuple(round(mix(v,w,a)) for v,w in zip(star_color(st.temperature),(102,67,45)))
                for line in wires(1):
                    c.line([(x+r*px,sy+r*py) for px,py in line],color,2)
                c.radius(x,sy,r)
            c.text(x,711,txt,39,INK,"center",a,face="serif")
        if t>=170:
            sub=ramp(t,170.4,174.5)*a
            if sub>.01:
                col=tuple(round(mix(v,w,sub)) for v,w in zip(star_color(st.temperature),(135,85,52)))
                for line in wires(2):c.line([(sx+big*px,sy+big*py) for px,py in line],col,1.7)
            reveal=ramp(t,172,174)*a
            lesson.equation(c,mix(sx,845,reveal),mix(701,797,reveal),"(2R)^{2} = 4R^{2}",40,GOLD,reveal)
            c.text(1312,797,"面积 ×4   光度 ×4",32,INK,"center",reveal)
    def dwarf_scale(self,c,t,st,v,a):
        r=173
        def tone(color):
            return tuple(round(mix(b,g,a)) for b,g in zip(getrgb(BG),getrgb(color)))
        c.circle(608,447,r,None,tone("#76918F"),3)
        c.circle(608,447,max(1.4,r*st.radius),tone(MINT))
        c.line([(614,447),(794,398),(v.sx-63,v.sy)],tone("#638785"),2)
        c.circle(v.sx,v.sy,70,None,tone("#637F83"),2)
        c.text(608,680,"太阳轮廓 · 同尺度",31,MUTED,"center",a)
        c.text(v.sx,v.sy+120,"局部放大",29,MUTED,"center",a)
    def notes(self,c,t,v,e,st,actual):
        q=self.c
        if e in {"follow","hydrogen","state"}:
            name={"follow":"初始质量约 1 M⊙ · 时间压缩","hydrogen":"漫长的主序","state":"状态的轨迹"}[e]
            c.text(v.sx,660,name,32,MUTED,"center")
        elif e=="leave":
            c.text(v.sx,695,"外层膨胀",38,INK,"center")
        elif e=="expand":
            self.temperature_reading(c,v,st)
        elif e=="area":
            x,y=project(v,*uv(st.temperature,st.luminosity))
            amount=1-ramp(t,153.0,153.55)
            if amount>.01:
                c.dashed(v.x,y,mix(v.x,x,ramp(t,152,152.5)),GOLD)
                accent(c,220,81,"总光度上升",f"约 {st.luminosity:.0f} L⊙",amount)
            accent(c,108,246,"红巨星半径",f"约 {st.radius:.0f} R⊙",ramp(t,153.6,154.4))
        elif e=="adjust":
            stage="红巨星支顶端 → 水平分支" if t<199 else "水平分支 → 再次膨胀"
            c.text(960,125,stage+"（简化）",34,MUTED,"center")
        elif e=="shed":c.text(108,260,"外层散去",48,INK,a=ramp(t,206,207.5),face="serif")
        elif e=="core":c.text(108,260,"核心显露",48,INK,face="serif")
        elif e in {"hotcore","fade"}:c.text(v.sx,672,"仍然明亮" if e=="hotcore" else "光度下降",31,MUTED,"center")
        elif e=="cool":c.text(v.sx,687,"余热散去",36,MUTED,"center")
        elif e=="recap1":
            c.text(960,102,"更热，就更亮？",50,INK,"center",1-ramp(t,308,312),"serif")
            p=ramp(t,308,312)
            c.text(660,103,"球面面积",41,GOLD,"center",p)
            c.text(960,103,"×",42,INK,"center",p)
            c.text(1250,103,"每平方米辐射功率",41,MINT,"center",p)
        elif e=="credits":
            a=ramp(t,325,326.4)
            c.text(960,102,"赫罗图与恒星演化",50,INK,"center",a,"serif")
            c.text(1823,883,"资料  UNL · ESA Gaia · OpenLearn · NASA / IAU",22,MUTED,"right",a)

    def temperature_reading(self,c,v,st):
        x,y=project(v,*uv(st.temperature,st.luminosity))
        original=evolved(self.c.anchor)
        reference,_=project(v,*uv(original.temperature,original.luminosity))
        bottom=v.y+v.h
        for yy in np.arange(v.y+25,bottom,18):
            c.line([(reference,yy),(reference,min(bottom,yy+8))],"#667F89",2)
        c.circle(reference,bottom,8,None,MUTED,2)
        c.line([(x,y+10),(x,bottom)],MINT,4)
        c.circle(x,bottom,8,MINT)
        marker(c,v,st)
        c.text(155,113,"表面温度",41,INK)
        c.text(485,62,"起始",27,MUTED,"center")
        c.text(845,62,"当前",27,MINT,"center")
        c.text(485,113,f"{original.temperature:.0f} K",48,MUTED,"center")
        c.text(665,113,"→",44,MUTED,"center")
        c.text(845,113,f"{st.temperature:.0f} K",57,MINT,"center")
        c.text(v.x+v.w, v.y-38,"局部放大",28,MUTED,"right")

class FilmCamera(Camera):
    def capture_mobjects(self,mobjects,**kwargs):
        if getattr(self,"shot",None) is None:return super().capture_mobjects(mobjects,**kwargs)
        self.set_pixel_array(np.asarray(self.shot.frame(self.progress.get_value()).convert("RGBA")))

class StellarAtlas(Scene):
    def __init__(self,**kwargs):super().__init__(camera_class=FilmCamera,**kwargs)
    def construct(self):
        cues=prepare()
        clock=StateClock(cues)
        for q in cues:
            progress=ValueTracker(q.start)
            self.camera.shot=Shot(q,config.pixel_width,config.pixel_height,clock)
            self.camera.progress=progress
            self.add(progress)
            self.play(progress.animate.set_value(q.end),rate_func=linear,run_time=q.end-q.start)
            self.remove(progress)



