# Synthesises the fictional demo voice note with the Windows speech engine.
# Run from the repo root:  powershell -File samples/voice/make_voice.ps1
# Then re-run samples/generate_samples.py so the fixture hash is updated.
Add-Type -AssemblyName System.Speech
$out = Join-Path $PSScriptRoot "voice_note_1.wav"
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth.SetOutputToWaveFile($out, $fmt)
$synth.Rate = -1
$synth.Speak("Sold two cartons of spaghetti, sixteen thousand naira. Bello took sugar on credit, seven thousand five hundred. Paid transport, one thousand five hundred.")
$synth.Dispose()
Write-Output "wrote $out"
