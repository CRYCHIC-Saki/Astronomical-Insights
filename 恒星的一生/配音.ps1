param([string]$Voice='Microsoft Huihui Desktop',[int]$Rate=1)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
Add-Type -AssemblyName System.Speech
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice)
$s.Rate=$Rate
$format=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(24000,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)
$null=New-Item 'build/phrases' -ItemType Directory -Force
try {
    foreach ($row in (Import-Csv '分镜.tsv' -Encoding utf8 -Delimiter "`t")) {
        $i=0
        foreach ($phrase in $row.旁白.Split('|')) {
            $file=Join-Path $PSScriptRoot ("build/phrases/{0}-{1}.wav" -f $row.事件,$i)
            $s.SetOutputToWaveFile($file,$format)
            $s.Speak($phrase)
            $s.SetOutputToNull()
            $i++
        }
    }
} finally { $s.Dispose() }
& '.\.venv\Scripts\python.exe' timing.py --join
exit $LASTEXITCODE
