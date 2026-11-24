"""Use measured phrase clips for picture cues, burned captions and the sound mix."""
import argparse
import csv
import filecmp
import hashlib
import json
import math
import tempfile
from pathlib import Path
import wave
from dataclasses import dataclass
import numpy as np
from physics import ROOT

OUT=ROOT/"输出"
OUT.mkdir(exist_ok=True)
RATE=24000
FPS=30
HOTCORE_HOLD=.50

def rows():
    with (ROOT/"分镜.tsv").open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f,delimiter="\t"))

def read_wav(path):
    with wave.open(str(path),"rb") as wav:
        assert (wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(RATE,1,2)
        return np.frombuffer(wav.readframes(wav.getnframes()),dtype="<i2")

def write_wav(path,data):
    with wave.open(str(path),"wb") as wav:
        wav.setparams((1,2,RATE,0,"NONE","not compressed"))
        wav.writeframes(data.tobytes())

def join(events=None):
    board=rows()
    selected=set(events or (r["事件"] for r in board))
    unknown=selected.difference(r["事件"] for r in board)
    if unknown:
        raise ValueError("未知分镜："+", ".join(sorted(unknown)))
    voice=ROOT/"voice"
    voice.mkdir(exist_ok=True)
    path=voice/"phrases.json"
    meta=json.loads(path.read_text(encoding="utf8")) if events and path.exists() else {}
    for row in board:
        event=row["事件"]
        if event not in selected:
            continue
        parts=[]
        phrases=[]
        cursor=0
        for i,txt in enumerate(row["旁白"].split("|")):
            data=read_wav(ROOT/"build"/"phrases"/f"{event}-{i}.wav")
            audible=np.flatnonzero(np.abs(data.astype(int))>60)
            if not audible.size:
                raise ValueError(f"{event}-{i}.wav 没有可用语音。")
            data=data[max(0,audible[0]-240):audible[-1]+241]
            phrases.append((txt,cursor,cursor+len(data)))
            gap=np.zeros(int(.19*RATE),dtype="<i2")
            parts.extend((data,gap))
            cursor+=len(data)+len(gap)
        data=np.concatenate(parts[:-1])
        write_wav(ROOT/"voice"/(event+".wav"),data)
        meta[event]={"sha256":hashlib.sha256(data).hexdigest(),"phrases":phrases}
    path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf8")

@dataclass
class Cue:
    chapter:str
    event:str
    plan:float
    next_plan:float
    anchor:float
    start:float
    end:float
    phrases:list

    @property
    def speech_start(self):return self.phrases[0][0]
    @property
    def speech_end(self):return self.phrases[-1][1]
    def caption(self,t):
        return next((txt for a,b,txt in self.phrases if a<=t<b),"")

def stamp(t):
    ms=round(t*1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"

def prepare():
    meta=json.loads((ROOT/"voice"/"phrases.json").read_text(encoding="utf8"))
    board=rows()
    frame=0
    cues,blocks,subs=[],[],[]
    for i,row in enumerate(board):
        e=row["事件"]
        p=float(row["计划起点"])
        q=float(board[i+1]["计划起点"]) if i+1<len(board) else 330
        data=read_wav(ROOT/"voice"/(e+".wav"))
        info=meta[e]
        if info["sha256"]!=hashlib.sha256(data).hexdigest() or row["旁白"].split("|")!=[s[0] for s in info["phrases"]]:
            raise ValueError(f"{e} 的录音或分句已更新，请重新合成分句。")
        lead=.30
        target=float(row.get("镜头秒数") or q-p)
        pauses=[float(s) for s in (row.get("句间加停/秒") or "").split(",") if s]
        if len(pauses)>len(info["phrases"])-1 or any(v<0 for v in pauses):
            raise ValueError(f"{e} 的句间停顿与分句数量不符。")
        extra=0
        aligned=[]
        for j,(txt,a,b) in enumerate(info["phrases"]):
            aligned.append((txt,a+extra,b+extra))
            if j<len(pauses):
                extra+=round(pauses[j]*RATE)
        count=max(round(target*FPS),math.ceil(((len(data)+extra)/RATE+lead+max(.55,HOTCORE_HOLD))*FPS))
        start=frame/FPS
        phrases=[(start+lead+a/RATE,start+lead+b/RATE,txt) for txt,a,b in aligned]
        cues.append(Cue(row["段落"],e,p,q,float(row["状态时间"]),start,(frame+count)/FPS,phrases))
        for a,b,txt in phrases:
            subs.append(f"{len(subs)+1}\n{stamp(a)} --> {stamp(b)}\n{txt}\n")
        block=np.zeros(count*(RATE//FPS),dtype="<i2")
        offset=round(lead*RATE)
        for (_,a,b),(_,lo,hi) in zip(info["phrases"],aligned):
            block[offset+lo:offset+hi]=data[a:b]
        blocks.append(block)
        frame+=count
    # Publish complete files even when several render presets start together.
    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        destination=Path(tmp)
        write_wav(destination/"普通话旁白.wav",np.concatenate(blocks))
        (destination/"中文字幕.srt").write_text("\n".join(subs),encoding="utf-8-sig")
        (destination/"中文旁白.txt").write_text("\n\n".join("".join(r["旁白"].split("|")) for r in board),encoding="utf-8-sig")
        with (destination/"实际分镜.tsv").open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.writer(f,delimiter="\t")
            writer.writerow(["入点/秒","出点/秒","事件","关注对象","动作","保留文字","转场","旁白"])
            for c,r in zip(cues,board):
                writer.writerow([round(c.start,3),round(c.end,3),c.event,r["关注对象"],r["画面"],r["保留文字"],r["转场"],r["旁白"].replace("|","")])
        for result in destination.iterdir():
            target=OUT/result.name
            if not target.exists() or not filecmp.cmp(result,target,shallow=False):
                result.replace(target)
    return cues

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--join",nargs="*",metavar="EVENT")
    options=parser.parse_args()
    if options.join is not None:
        join(options.join)
    cs=prepare()
    print(len(cs),"shots,",round(cs[-1].end,3),"seconds")



