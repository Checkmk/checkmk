# Guest-side: block until the guest has settled, so its saved state
# (bazel/tools/windows_vm/save_state.py) has the post-logon background
# work (licensing, .NET optimisation, ...) done instead of replaying it on
# every resume.
# Idle = total CPU below -MaxPercent for -Windows consecutive 10 s windows.
# Exits 1 after -TimeoutSec without reaching that; the caller decides.
param([int]$MaxPercent = 10, [int]$Windows = 3, [int]$TimeoutSec = 300)

# Stopwatch, not Get-Date: w32time may step the clock meanwhile.
$sw = [Diagnostics.Stopwatch]::StartNew()
$idle = 0
while ($idle -lt $Windows) {
    if ($sw.Elapsed.TotalSeconds -ge $TimeoutSec) {
        Write-Output "not idle after $TimeoutSec s"
        exit 1
    }
    # MaxSamples 1 with a 10 s interval cooks one value over the whole window.
    $pct = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 10 -MaxSamples 1).CounterSamples[0].CookedValue
    if ($pct -lt $MaxPercent) { $idle++ } else { $idle = 0 }
    Write-Output ('{0,4:N0} s: {1,5:N1} % CPU' -f $sw.Elapsed.TotalSeconds, $pct)
}
Write-Output "idle ($Windows x 10 s below $MaxPercent % CPU) after $([int]$sw.Elapsed.TotalSeconds) s"
