# Guest-side: empty Windows' file cache right before the VM state is saved
# (bazel/tools/windows_vm/save_state.py). The state holds every non-zero
# guest page, and after boot the standby list is much of the guest's RAM:
# unpurged, a saved state was 2.87 GiB and took 6-8 s to load. Purged, the
# pages go to the free list, the zero-page thread zeroes them, and the
# save skips them: about 1 GiB and 2-3 s. Resumed guests start with a cold
# file cache, which costs only the first read of each file. It returns once
# the zero-page thread has emptied the free list (or after -TimeoutSec).
# Exits non-zero if either list operation fails; the caller decides.
param([int]$TimeoutSec = 60)
$src = @'
using System;
using System.Runtime.InteropServices;
public static class MemoryList {
    [DllImport("ntdll.dll")] static extern int NtSetSystemInformation(int cls, ref int info, int len);
    [DllImport("ntdll.dll")] static extern int NtQuerySystemInformation(int cls, IntPtr info, int len, out int ret);
    [DllImport("ntdll.dll")] static extern int RtlAdjustPrivilege(int priv, bool enable, bool thread, out bool was);
    public static int Run(int command) {
        bool was;
        RtlAdjustPrivilege(13, true, false, out was); // SeProfileSingleProcessPrivilege
        return NtSetSystemInformation(80, ref command, 4); // SystemMemoryListInformation
    }
    // Pages on the free list, not zeroed yet: FreePageCount, the second
    // field of SYSTEM_MEMORY_LIST_INFORMATION.
    public static long FreePages() {
        bool was;
        RtlAdjustPrivilege(13, true, false, out was);
        IntPtr info = Marshal.AllocHGlobal(256);
        try {
            int ret;
            int status = NtQuerySystemInformation(80, info, 256, out ret);
            if (status != 0) { throw new Exception(String.Format("NtQuerySystemInformation 0x{0:X}", status)); }
            return Marshal.ReadInt64(info, 8);
        } finally { Marshal.FreeHGlobal(info); }
    }
}
'@
Add-Type -TypeDefinition $src

function Show([string]$label) {
    $s = (Get-Counter '\Memory\Standby Cache Normal Priority Bytes',
        '\Memory\Standby Cache Reserve Bytes',
        '\Memory\Free & Zero Page List Bytes').CounterSamples
    Write-Output ('{0}: standby {1:N0} MB, free+zero {2:N0} MB' -f $label,
        (($s[0].CookedValue + $s[1].CookedValue) / 1MB), ($s[2].CookedValue / 1MB))
}

Show 'before'
$flush = [MemoryList]::Run(3)  # MemoryFlushModifiedList
$purge = [MemoryList]::Run(4)  # MemoryPurgeStandbyList
Show 'after'
if ($flush -ne 0 -or $purge -ne 0) {
    Write-Output ('failed: flush 0x{0:X}, purge 0x{1:X}' -f $flush, $purge)
    exit 1
}
# The save skips zeroed pages only: wait until the zero-page thread is done.
$sw = [Diagnostics.Stopwatch]::StartNew()
while (($free = [MemoryList]::FreePages() * 4KB) -gt 16MB -and $sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
    Start-Sleep -Milliseconds 500
}
Write-Output ('{0:N0} MB not zeroed after {1:N1} s' -f ($free / 1MB), $sw.Elapsed.TotalSeconds)
