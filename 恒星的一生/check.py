"""Check the delivered media, phrase alignment, every edit and the physical track."""
import argparse
import json
import math
import wave

import av
import numpy as np
import srt
from PIL import Image, ImageDraw

from camera_track import StateClock, camera, project
from art import font, uv
from luminosity import numbers
from film import Shot
from physics import BOTTOM, LEFT, RIGHT, ROOT, TIMES, TOP, TRACK, TSUN, evolved, hr_to_point
from render import PRESETS, interval
from timing import HOTCORE_HOLD, OUT, prepare


def inspect_track(cues):
    clock = StateClock(cues)
    for row, t in zip(TRACK, TIMES):
        star = evolved(t)
        assert math.isclose(star.temperature, float(row["temperature_K"]), rel_tol=1e-10)
        assert math.isclose(star.luminosity, float(row["luminosity_Lsun"]), rel_tol=1e-10)
    for t in np.linspace(TIMES[0], TIMES[-1], 10000):
        star = evolved(t)
        x, y = hr_to_point(star.temperature, star.luminosity)
        assert LEFT <= x <= RIGHT and TOP <= y <= BOTTOM
        assert math.isclose(star.radius**2 * (star.temperature / TSUN)**4, star.luminosity, rel_tol=1e-12)
        i = max(1, min(len(TIMES)-1, np.searchsorted(TIMES, t)))
        for key, value in (("temperature_K", star.temperature), ("luminosity_Lsun", star.luminosity)):
            lo, hi = sorted(float(TRACK[j][key]) for j in (i-1, i))
            assert lo*(1-1e-10) <= value <= hi*(1+1e-10), (t, key, value)
        if t >= 275:
            assert abs(star.radius - .013) < .00003
    times = np.linspace(clock.start, clock.end, 2401)
    assert np.all(np.diff([clock(t) for t in times]) >= -1e-10)
    by_event={q.event:q for q in cues}
    reading=by_event["expand"]
    view=camera(reading.plan)
    xs=[]
    temperatures=[]
    for now in np.linspace(reading.start,reading.end,241):
        star=evolved(clock(now))
        temps_view=camera(reading.plan+(reading.next_plan-reading.plan)*(now-reading.start)/(reading.end-reading.start))
        assert temps_view==view
        x,y=project(view,*uv(star.temperature,star.luminosity))
        assert view.x<=x<=view.x+view.w and view.y<=y<=view.y+view.h
        xs.append(x)
        temperatures.append(star.temperature)
    assert np.all(np.diff(xs)>=-1e-7) and np.all(np.diff(temperatures)<=1e-6)
    assert round(temperatures[0])==TSUN and round(temperatures[-1])==3500 and xs[-1]-xs[0]>160
    for first,stop,rgb in [("windows","adjust",True),("example","cool",False)]:
        at=by_event[first].start
        star=evolved(clock(at))
        for now in np.linspace(at,by_event[stop].start,101):
            state=evolved(clock(now))
            assert np.allclose([state.temperature,state.radius,state.luminosity],
                               [star.temperature,star.radius,star.luminosity],rtol=1e-9)
        area,flux,total=numbers(star)
        assert math.isclose(total,star.luminosity,rel_tol=1e-12)
        if rgb:
            assert (round(area,-2),round(flux,3),round(total))==(7400,.135,1000)
        else:
            assert (round(area,6),round(flux),round(total,3))==(.000169,144,.024)


def check_subs(cues):
    subs = list(srt.parse((OUT / "中文字幕.srt").read_text(encoding="utf-8-sig")))
    expected = [p for cue in cues for p in cue.phrases]
    assert len(subs) == len(expected)
    for i, (sub, (start, end, txt)) in enumerate(zip(subs, expected), 1):
        assert sub.index == i and sub.content == txt and "\n" not in txt
        assert font("msyh.ttc", 39).getlength(txt) < 1780, (i, txt)
        assert abs(sub.start.total_seconds()-start) <= .00051
        assert abs(sub.end.total_seconds()-end) <= .00051
    return len(subs)


def save_sheet(path, cells, columns=3):
    w, h = 320, 180
    sheet = Image.new("RGB", (columns*w, ((len(cells)+columns-1)//columns)*(h+22)), "#0b1420")
    draw = ImageDraw.Draw(sheet)
    for i, (label, thumb) in enumerate(cells):
        x, y = i%columns*w, i//columns*(h+22)
        sheet.paste(thumb, (x, y))
        draw.text((x+6, y+h+3), label, fill="white")
    sheet.save(path, quality=89)


def inspect_video(path, mode, cues, start, end, hold):
    w, h, fps, _ = PRESETS[mode]
    count = round((end-start)*fps)
    included = [q for q in cues if q.end > start and q.start < end]
    groups = []
    marks = {}
    for q in included:
        begin = max(0, round((q.start-start)*fps))
        stop = min(count, round((q.end-start)*fps))
        indices = [begin, (begin+stop)//2, stop-1]
        groups.append((q.event, indices))
        for i in indices:
            marks[i] = None
    seams = {indices[0]: name for name, indices in groups[1:]}
    changes = []
    hold_grids = []
    previous = None
    experiment = next((q for q in included if q.event == "double"),None)
    moving_at = experiment.start+.43*(experiment.end-experiment.start) if experiment else float("inf")
    previous_surface = None
    moving_pairs = []
    with av.open(str(path)) as movie:
        video = movie.streams.video[0]
        assert (video.width, video.height, float(video.average_rate)) == (w, h, fps)
        codec = video.codec_context.name
        video.thread_type = "AUTO"
        decoded = 0
        for i, frame in enumerate(movie.decode(video)):
            assert frame.pts is not None and abs(frame.time-i/fps) < .0001
            plane = frame.planes[0]
            luma = np.frombuffer(plane, dtype=np.uint8).reshape(-1, plane.line_size)[:h, :w]
            grid = luma[::12, ::12]
            assert luma[::5, ::5].max() > 90, ("dark frame", i)
            if i in marks:
                marks[i] = frame.to_image().resize((320, 180), Image.Resampling.LANCZOS)
            if i in seams:
                delta = np.abs(previous.astype(np.int16)-grid).mean()
                changes.append((seams[i], round(float(delta), 3)))
            if moving_at <= start+frame.time < moving_at+2:
                surface = luma[h//4:2*h//3:4, w//2:4*w//5:4]
                if previous_surface is not None:
                    moving_pairs.append(bool(np.any(np.abs(surface.astype(np.int16)-previous_surface) > 3)))
                previous_surface = surface.copy()
            if hold[0]-1e-8 <= start+frame.time < hold[1]-1e-8:
                hold_grids.append(grid.astype(np.int16))
            previous = grid.copy() if i+1 in seams else None
            decoded += 1
    assert decoded == count
    if experiment:
        assert len(moving_pairs) >= 2*fps-2
        assert np.mean(moving_pairs) > .75, "experimental sphere lacks intermediate motion"
    if start <= hold[0] and end >= hold[1]:
        assert len(hold_grids) == round(HOTCORE_HOLD*fps)
        assert max(np.abs(current-hold_grids[0]).mean() for current in hold_grids) < .5
    assert all(img is not None for img in marks.values())
    cells = [(f"{name}   {i/fps+start:.2f} s", marks[i]) for name, indices in groups for i in indices]
    build = ROOT / "build"
    for k in range(0, len(cells), 24):
        save_sheet(build/f"{mode}-shots-{k//24+1}.jpg", cells[k:k+24])
    clock = StateClock(cues)
    source_errors = []
    for cue, (_, indices) in zip(included, groups):
        i = indices[1]
        source = Shot(cue, w, h, clock).frame(start+i/fps)
        sample = source.resize((320, 180), Image.Resampling.LANCZOS)
        error = np.abs(np.asarray(sample, dtype=np.int16)-np.asarray(marks[i])).mean()
        assert error < 3, ("source/encode mismatch", cue.event, error)
        source_errors.append(float(error))
    return dict(frames=decoded, fps=fps, width=w, height=h, video=codec,
                shots=len(groups), seam_luma_mean_difference_8bit=dict(changes),
                maximum_source_to_encode_mean_RGB_difference_8bit=max(source_errors),
                expanding_sphere_adjacent_pairs=len(moving_pairs),
                expanding_sphere_visibly_changed_pairs=sum(moving_pairs))


def inspect_sound(path, cues, start, end, hold):
    with av.open(str(path)) as movie:
        stream = movie.streams.audio[0]
        rate, codec = stream.rate, stream.codec_context.name
        sound = np.concatenate([f.to_ndarray().astype("float32").ravel() for f in movie.decode(stream)])
    assert abs(len(sound)/rate-(end-start)) < .10
    with wave.open(str(OUT / "普通话旁白.wav"), "rb") as wav:
        assert wav.getframerate() == rate
        wav.setpos(round(start*rate))
        ref = np.frombuffer(wav.readframes(round((end-start)*rate)), dtype="<i2")
    correlations = []
    for cue in cues:
        for a, b, txt in cue.phrases:
            lo = max(0, round((a-start)*rate))
            hi = min(len(ref), round((b-start)*rate))
            if hi-lo < rate*.1:
                continue
            clip = sound[lo:hi]
            assert np.sqrt(np.mean(clip**2)) > .002, (cue.event, txt)
            corr = float(np.corrcoef(clip, ref[lo:hi])[0, 1])
            assert corr > .94, (cue.event, txt, corr)
            correlations.append(corr)
    if start <= hold[0] and end >= hold[1]:
        pause = sound[round((hold[0]-start+.025)*rate):round((hold[1]-start)*rate)]
        assert np.sqrt(np.mean(pause**2)) < .001
    return dict(audio=codec, audio_rate=rate, decoded_audio_seconds=len(sound)/rate,
                verified_phrases=len(correlations), minimum_voice_correlation=min(correlations))


def check(mode):
    cues = prepare()
    inspect_track(cues)
    captions = check_subs(cues)
    start, end = interval(cues, mode)
    hot = next(q for q in cues if q.event == "hotcore")
    assert hot.end - hot.speech_end >= HOTCORE_HOLD
    hold = (hot.end-HOTCORE_HOLD, hot.end)
    path = OUT / (PRESETS[mode][3]+".mp4")
    report = dict(file=path.name, seconds=end-start, start_in_master=start,
                  master_caption_count=captions, physics_samples=10000)
    report.update(inspect_video(path, mode, cues, start, end, hold))
    report.update(inspect_sound(path, cues, start, end, hold))
    data = json.dumps(report, ensure_ascii=False, indent=2)
    (ROOT/"build"/f"{mode}-check.json").write_text(data, encoding="utf8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=PRESETS)
    check(parser.parse_args().mode)

