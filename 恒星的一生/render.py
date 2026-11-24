"""Render native intermediate states and mux the matching range of the voice track."""
import argparse
from fractions import Fraction
import subprocess
import av
import imageio_ffmpeg
from manim import config
from film import Shot
from camera_track import StateClock
from timing import ROOT,OUT,prepare

PRESETS={"opening":(1280,720,30,"开场提问小样"),"sample":(1280,720,30,"膨胀联动小样"),
         "formula":(1280,720,30,"定量推理小样"),"preview":(1280,720,30,"全片预览"),
         "final":(1920,1080,60,"赫罗图与恒星演化")}
def interval(cues,mode):
    selections={"opening":("open","hot"),"sample":("leave","windows"),"formula":("windows","adjust")}
    if mode in selections:
        starts={q.event:q.start for q in cues}
        a,b=selections[mode]
        return starts[a],starts[b]
    return 0,cues[-1].end

def export(mode):
    w,h,fps,name=PRESETS[mode]
    cues=prepare()
    clock=StateClock(cues)
    begin,end=interval(cues,mode)
    build=ROOT/"build"
    build.mkdir(exist_ok=True)
    config.media_dir=str(build/"manim")
    path=build/(mode+".video.mp4")
    with av.open(str(path),"w") as movie:
        stream=movie.add_stream("libx264",rate=fps)
        stream.width,stream.height,stream.pix_fmt=w,h,"yuv420p"
        stream.options={"preset":"ultrafast","crf":"18","threads":"4"}
        n=0
        for q in cues:
            if q.end<=begin or q.start>=end:continue
            shot=Shot(q,w,h,clock)
            print(mode,q.event,round(q.start,2),flush=True)
            stop=round((min(end,q.end)-begin)*fps)
            while n<stop:
                image=shot.frame(begin+n/fps)
                vf=av.VideoFrame.from_image(image)
                vf.pts=n
                vf.time_base=Fraction(1,fps)
                for packet in stream.encode(vf):movie.mux(packet)
                n+=1
        for packet in stream.encode():movie.mux(packet)
    muxed=build/(mode+".mux.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-y","-loglevel","error","-i",str(path),
                    "-ss",str(begin),"-i",str(OUT/"普通话旁白.wav"),"-t",str(n/fps),
                    "-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","128k","-movflags","+faststart",str(muxed)],check=True)
    muxed.replace(OUT/(name+".mp4"))
    print(f"{name}: {n} frames, {n/fps:.3f} s",flush=True)
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=PRESETS)
    export(parser.parse_args().mode)

