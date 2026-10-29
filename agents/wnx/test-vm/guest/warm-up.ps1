# Guest-side: work that Windows does on first use, done once before the VM
# state is saved (bazel/tools/windows_vm/save_state.py, ahead of
# wait-idle.ps1, which then waits for it to settle) instead of in every
# test that comes first after a resume. Each warm-up says why it is here.

# Stopwatch, not Get-Date: w32time may step the clock meanwhile.
$sw = [Diagnostics.Stopwatch]::StartNew()

# The first query of root\WMI keeps the WMI service busy for 13 to 19 s.
# OHM's first start reads SMBIOS there (watest's SectionProviderOhm tests).
$null = Get-CimInstance -Namespace root\WMI -ClassName MSSmBios_RawSMBiosTables -ErrorAction SilentlyContinue
Write-Output ('{0,4:N0} s: root\WMI queried' -f $sw.Elapsed.TotalSeconds)

# The first query of a performance class in root\cimv2 starts WMI's
# performance provider: about 4 s, which watest's WMI sections paid
# (WmiProviderTest.WmiSubSection_Component, WmiProviderTest.DelayOnFailShift).
$null = Get-CimInstance -ClassName Win32_PerfRawData_PerfOS_System -ErrorAction SilentlyContinue
Write-Output ('{0,4:N0} s: performance classes queried' -f $sw.Elapsed.TotalSeconds)
