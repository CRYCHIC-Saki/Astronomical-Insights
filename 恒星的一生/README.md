# 赫罗图与恒星演化 · 第三轮

全片 6 分 13.5 秒。开头用几颗颜色不同、符号等大的恒星提出“更热，就更亮？”。观众先学会读赫罗图，然后从星群中选定一颗初始质量约为一个太阳质量的单星，跟踪它的表面温度、半径和总光度。

## 观看

| 文件 | 规格与内容 |
| --- | --- |
| `输出/赫罗图与恒星演化.mp4` | 1920 × 1080，原生 60 fps，373.5 秒。H.264 视频、AAC 普通话配音和烧录字幕 |
| `输出/全片预览.mp4` | 1280 × 720，原生 30 fps，与成片同长 |
| `输出/开场提问小样.mp4` | 27 秒，独立示例、提问、太阳收束为坐标标记 |
| `输出/膨胀联动小样.mp4` | 31 秒，原表面轮廓、14 秒稳定的温度读图、光度投影与巨星半径 |
| `输出/定量推理小样.mp4` | 78.4 秒，等面积窗口、全波段辐射、同温球面、太阳单位计算和结果回图 |
| `输出/中文字幕.srt`、`输出/中文旁白.txt`、`输出/普通话旁白.wav` | 独立字幕、中文定稿与带停顿的完整音轨 |
| `分镜.tsv`、`输出/实际分镜.tsv` | 可编辑的分镜主稿，以及 39 个镜头的实际入点、出点、动作、文字、转场和旁白 |

## 本轮镜头

| 成片位置 | 画面和声音 |
| --- | --- |
| 00:00–00:27 | 几颗不同的恒星引出总能量问题。选择太阳示范如何定位，逐步引入坐标。 |
| 01:58 | 完成星群和主序带的讲解后，引入持续追踪的类太阳单星，注明时间压缩。 |
| 02:30.6–02:44.6 | 赫罗图保持稳定。灰色虚线和空心点标出起始 5772 K，青色线连接活动点和温度轴，终值 3500 K。轨迹始终保留实际的横向、纵向分量。随后单独读取约 1000 L⊙ 的高度。 |
| 02:53.1–04:11.5 | 主角停在红巨星状态。从太阳和巨星各取一块标为 1 m² 的表面窗口，比较全部波段的辐射功率。用球面网格做同温控制变量实验，再将巨星的两个倍率汇合，返回同一图点。 |
| 05:18.4–05:44.4 | 在白矮星冷却途中停下 26 秒，用相同的位置和颜色再算一次。随后继续沿冷却轨迹向右下移动。 |
| 05:55.4–06:13.5 | 回到完整赫罗图，以表面积和每平方米辐射功率回答开头的问题，从状态点收束到演化轨迹。 |

## 两次计算

依据斯特藩–玻尔兹曼关系，单个表面窗口用有效表面温度描述全波段辐射通量，单位为 W/m²。把通量乘上球面面积，得到整颗星的光度。图中量条编码功率，恒星纹理与屏幕亮度用于直观辨认。太阳名义有效温度采用 5772 K。[内布拉斯加大学讲义](https://astro.unl.edu/newRTs/Luminosity/Background/HR_Luminosity1.html) · [NASA 太阳参数](https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html) · [IAU B3 名义太阳单位](https://www.iau.org/common/Uploaded%20files/IAUGA2015-Resolution-B3-recommended-nominal-conversion.pdf)

`F_surf = σ T_eff⁴`　　`L = 4πR² F_surf`

| 教学状态 | 总表面积 / 太阳表面积 | 单位面积辐射功率 / 太阳值 | 总光度 / 太阳光度 |
| --- | ---: | ---: | ---: |
| 红巨星，3500 K，约 86 R⊙ | 86² = 7396，约 7400 | (3500/5772)⁴ ≈ 0.135 | 约 1000 |
| 冷却途中的白矮星，20 000 K，约 0.013 R⊙ | 0.013² ≈ 0.000169 | (20 000/5772)⁴ ≈ 144 | 约 0.024 |

演化函数从原有 `track.csv` 取温度与光度，逐帧由 `R/R⊙ = √(L/L⊙) × (5772 K / T_eff)²` 推导半径。乘式用适于阅读的舍入数，图点使用未舍入光度 1000、0.02436。白矮星取值是冷却中的一个样本，随后它会继续冷却。片中有简化的核心氦燃烧、再次膨胀和热中心星阶段。

背景星群、光谱颜色、气壳和教学时间轴均为示意。主图使用固定函数压缩物理半径，再应用相机倍率。温度轴始终向右降低，光度轴向上增大，两者取对数。等面积窗口表示一样大的物理表面，球面倍增实验使用局部真实半径比。白矮星的同尺度轮廓和单独放大视图均有标注。

## 修改与重新渲染

在 Windows 的工程目录中运行。解压到新电脑后，先安装 64 位 Python 3.12 和锁定的依赖。工程使用 Manim Community 0.19.2、微软雅黑、宋体、Cambria；迁移平台时需调整 `art.py`、`luminosity.py` 中的字体配置。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

使用包内配音可以直接渲染。三个小样和整片共用 `StellarAtlas` 的绘图函数、物理时钟与镜头。`render.py` 逐帧求值，合成动态层并自动加入普通话配音。

```powershell
.\.venv\Scripts\python.exe render.py opening
.\.venv\Scripts\python.exe render.py sample
.\.venv\Scripts\python.exe render.py formula
.\.venv\Scripts\python.exe render.py preview
.\.venv\Scripts\python.exe render.py final
.\.venv\Scripts\python.exe check.py final
```

标准 Manim 命令行可单独生成画面轨。

```powershell
.\.venv\Scripts\python.exe -m manim --disable_caching -r 1920,1080 --fps 60 film.py StellarAtlas
```

- **旁白与字幕。** 编辑 `分镜.tsv`，用 `|` 划分单行字幕。“镜头秒数”设定期望的最短镜头时长。“句间加停/秒”用逗号分隔，依次为相邻两句之间增加静音。配音超出镜头时，镜头会延长。运行 `.\配音.ps1`，沿用 Windows 普通话音色 Microsoft Huihui Desktop 和原有语速参数 1。语音由实际分句时长对齐。
- **真人配音。** 如需替换某一镜头，把各句录作 24 kHz、单声道、16 位 PCM WAV，按顺序保存为 `build/phrases/事件名-0.wav`、`事件名-1.wav` 等。以 `example` 为例，运行 `.\.venv\Scripts\python.exe timing.py --join example`，再重新渲染。工程需同时保留分镜使用的 `voice/*.wav` 与 `voice/phrases.json`。
- **画面。** `camera_track.py` 控制独立的镜头视窗和状态时钟。`physics.py` 计算物理量，`art.py` 缓存底图、纹理与字形。`film.py` 负责读图、投影、同温球面和字幕。`luminosity.py` 实现等面积窗口、量条、公式上下标与因子移动。两次演算直接读取相应恒星状态。
- **复核。** `check.py` 接受五个与渲染同名的模式。检查视频逐帧时间戳、黑帧、全部镜头接点、语音波形与字幕时间，抽样校验物理轨迹、温度右移、实验期间的恒星状态，以及白矮星的冷却半径。检查报告保存在 `build/*-check.json`。

## 科学资料与制作参考

- 反向温度轴、光度轴、三个区域及等半径线的物理关系依据内布拉斯加大学的教学材料。 [UNL · The Hertzsprung–Russell Diagram](https://astro.unl.edu/naap/hr/hr_background3.html)
- 分布图展示许多不同恒星。Gaia 的观测图提供了这种群体视角。本片从固定种子 5772 生成背景星点。 [ESA · Gaia’s Hertzsprung–Russell diagram](https://www.esa.int/media/gaia-s-hertzsprung-russell-diagram)
- 主序、红巨星、水平分支和第二次巨星阶段参考英国开放大学的生命周期教材。类太阳低质量星在核心氦燃烧期间对应红团簇一侧。 [OpenLearn · The life cycle of stars](https://www.open.edu/openlearn/science-maths-technology/white-dwarfs-and-neutron-stars/content-section-3) · [OpenLearn · Expansion and the red giant branch](https://www.open.edu/openlearn/mod/oucontent/view.php?id=141781&section=_unit8.2.2) · [Serenelli 等，2017，A&A 606, A33](https://www.aanda.org/articles/aa/pdf/2017/10/aa31004-17.pdf)
- 失去外层后的升温、高光度中心星和后续白矮星冷却，参照开放大学教材与后渐近巨星支模型的定性走向。本片自行选取锚点。 [OpenLearn · Planetary nebulae](https://www.open.edu/openlearn/science-maths-technology/white-dwarfs-and-neutron-stars/content-section-4) · [Miller Bertolami 2016](https://doi.org/10.1051/0004-6361/201526577)
- 5772 K 的太阳有效温度和太阳单位基准。 [NASA · Sun Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html) · [IAU 2015 Resolution B3](https://www.iau.org/common/Uploaded%20files/IAUGA2015-Resolution-B3-recommended-nominal-conversion.pdf)
- 先呈现现象、再让图像解释关系的导演方法参考 3Blue1Brown。本片台词与视觉素材均为原创。 [3Blue1Brown · About](https://www.3blue1brown.com/about/)
- 矢量文字和场景使用 Manim Community；声音采用独立语音片段实测长度来安排画面。 [Manim · Rendering Text and Formulas](https://docs.manim.community/en/stable/guides/using_text.html) · [Manim · Adding Voiceovers](https://docs.manim.community/en/stable/guides/add_voiceovers.html)
