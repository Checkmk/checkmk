# Windows test VM

The `*-qemu` test tiers run cross-built Windows payloads (watest, the regression and
integration suites, Pester, the Rust tests of cmk-agent-ctl, mk-sql and mk-oracle, the
MSI install) inside a real Windows Server 2022 VM, driven from Linux. This directory
builds that VM's image and the saved state the tests start from.

## How a test gets its VM

1. The image (`@win2022_core_image`, pinned in `image.bzl`): Windows Server 2022
   Datacenter Evaluation, Server Core, provisioned by `make_image.py` and cleanly shut
   down. Published on Nexus upstream-archives; shared by CI and developers.
2. The VM state (`:core-state`, `bazel/rules/xcomp/windows_vm_state.bzl`): a Bazel
   action boots the image once, does the work Windows would otherwise do on first use
   in every test (`guest/warm-up.ps1`), waits until the guest has settled and saves the
   running VM (a small disk overlay plus the RAM and device state, about 1 GiB). It runs on the
   build host, because the state only resumes on the same CPU (`-cpu host`): the host's
   CPU as the pinned QEMU sees it (`@qemu_host_cpu`) is part of its cache key. About 3
   to 5 minutes, then cached (disk cache, bazel-remote).
3. Each test resumes that state in its own VM on a throwaway disk layer
   (`bazel/tools/windows_vm/qemu_windows/state.py`), in a few seconds, and the
   VM ends with the test.

Every VM, from the image build on, has the size that `WINDOWS_TEST_VM` in `image.bzl`
sets (4 vCPUs, 4 GiB of RAM): a state only resumes with the size it was saved with.

QEMU itself is `@qemu_linux_x86_64`, a static build from `third_party/qemu`. So building
the image and the tests need `/dev/kvm` (readable and writable, e.g. through the kvm
group) and the host's `setpriv`, but no QEMU package. The first test run downloads the
image (about 5 GiB: 30 to 45 minutes over the VPN), once per image version and machine.
The guest's user and password are fixed test values (`USER` and `PASSWORD` in
`bazel/tools/windows_vm/qemu_windows/guest.py`): the host reaches the VM only
through its own sockets (see "Reaching a guest"). The password is baked into the
image, so changing it takes a new image.

The CPU fingerprint is taken once and then only re-read when QEMU, the CPU (model,
features, microcode) or the kernel changes, not when a KVM module parameter or the kernel
command line changes the features KVM passes on. The state action and every test check it against the host CPU and say
when it is out of date, also when it was taken without usable KVM (before joining the
kvm group, in a container without `/dev/kvm`); refresh it with
`bazel fetch --force --repo=@qemu_host_cpu`.

The guests have unrestricted network access through QEMU's user-mode NAT: the host as
10.0.2.2 (mk-oracle's database tests use that) and whatever the host itself reaches.
Tests should not depend on the internet; nothing enforces that.

## Exploring the test VM

`winvm` starts the VM a test would get, after the same checks a test makes, and works
with it. It is in `bazel_env` (`bazel run //bazel/tools:bazel_env`); in a checkout
without that, `bazel run //agents/wnx/test-vm:winvm -- ARGS` does the same.

```
winvm start                    # PowerShell in this terminal; exit ends the VM
winvm start --headless         # in the background; prints the VM's ID
winvm list                     # ID, age, worktree, log
winvm put LOCAL [REMOTE]       # into C:\ by default, or into a guest directory
winvm get REMOTE [LOCAL]       # into the working directory by default
winvm exec -- Get-Service qemu-ga
winvm stop [--all]             # ends the VM, or all of yours
```

`winvm start` runs `core-vm` through Bazel in the checkout of the working directory:

```
bazel run --config=test-vm //agents/wnx/test-vm:core-vm
```

so the first start after a change to the image or the VM state builds the state, a few
minutes. `winvm` itself needs neither the image nor `--config=test-vm`.

### The shell

`winvm start` (or `core-vm`) switches your terminal to PowerShell on the VM's serial
console, as the Administrator. The VM is saved with that PowerShell already logged in,
in SAC's first `cmd` channel (`Cmd0001`, see "Reaching a guest"), so its prompt shows
about a second after the resume. `exit` ends that PowerShell and the VM with it (Ctrl-]
does the same for a PowerShell that hangs). The VM's disk layer goes with it: the next
start is the saved state again.

The session's console host lays out its screen for your terminal's size, and is switched
to again when the terminal is resized, so that it redraws for the new size. SAC drops
the ESC that cursor keys start with, so the shell sends the arrow keys, Home, End and
Delete as control keys that the session's PSReadLine binds to them (Ctrl+P, N, F, B, A,
E and D; `KEY_BINDINGS` in `qemu_windows/console.py`). Output comes at serial speed: a
full listing of `C:\Windows\system32` takes about 10 s.

### Without a terminal

`winvm start --headless` runs `core-vm -- --no-shell` in the background, in a session of
its own, and returns once its VM runs, printing its ID alone. While Bazel fetches the
image or builds the VM state it says so and waits as long as that takes (Ctrl-C stops
the start); once `core-vm` runs, its VM is due within 5 minutes. `core-vm`'s output goes
to a log in the registry directory (`start-<token>.log`, which `winvm list` names): it
outlives the VM, so it still tells why a VM ended, for a day, and `winvm start` shows the
end of a failed start's log. For an agent:

```
id=$(winvm start --headless)
winvm exec --vm "$id" -- '(Get-CimInstance Win32_OperatingSystem).Caption'
winvm stop --vm "$id"
```

## Working with running test VMs

Every `core-vm` registers its VM for `winvm` under a short ID (`vm1`, `vm2`, ...), in
`$XDG_RUNTIME_DIR/qemu-windows` (`vm_registry.py`); `winvm start --headless` finds its
own by a token it hands `core-vm`. `--vm ID` picks the VM and may be left out while only
one runs.

Guest paths start with their drive and take `/` or `\` (`C:/Program Files/x.log`).
`put`, `get` and `exec` go through the guest agent as LocalSystem, one command at a time
per VM; `exec` runs in `C:\`, reads the output back as a file (the agent's own output
capture runs at about 8 KB/s) and exits with the script's exit code. They work on a VM
whose shell is open too, from another terminal.

`winvm completion bash|zsh|nu` prints the completion script, which also completes
guest paths after `get` and `put LOCAL` by listing the guest directory:
`eval "$(winvm completion bash)"` in bash, and in nushell
`winvm completion nu | save -f ~/.config/nushell/winvm-completions.nu` and
`use winvm-completions.nu *` (a module named `winvm` cannot export the `winvm` extern).

## What is in the image

`make_image.py` runs three QEMUs, each ended by a clean guest shutdown, so every boot
after the install is a cold one with only the devices it needs:

1. Install: Windows Setup (Server Core) from the Eval ISO, with the answer file on a
   virtual floppy (`answer/`), then `guest/first-logon.ps1`: the guest agent (qemu-ga)
   and its virtio-serial driver from the virtio-win ISO, EMS on COM1 (the serial
   console), Defender removed, Windows Update off, Windows' test-signing mode (for
   OHM's WinRing0 driver), a fixed 256 MB pagefile, permanent autologon of the
   Administrator (the runners execute in that console session through a scheduled
   task: run-as spawns and COM services need it), Berlin time zone (watest expects
   it), the RTC in UTC (the runner sets the guest clock from the host after each
   resume), no password expiry, and the mount point the agent tests look for. It
   then powers the guest off: until then, the build has no channel into the guest.
2. Provisioning: first-logon.ps1's result, Eval activation, SQL Server 2022 Developer
   with the three instances the mk-sql tests expect (`guest/install-mssql.ps1`, from
   the SQL ISO on a CD drive), an NGEN flush, a component store cleanup, the removal
   of `C:\setup` (its logs go to the build's work directory) and a TRIM.
3. Verification: the device set the tests use, and `guest/verify-image.ps1`.

## Building a new image

The Eval licence runs 180 days from the build (`image.bzl` records its end; the
tests and `core-vm` refuse to start the VM from the day before). Build and
publish a new image with the manual Jenkins job
`buildscripts/scripts/winagt-build-test-vm-image.groovy`, which runs

```
bazel run --config=test-vm //agents/wnx/test-vm:build-core -- --out <dir>/<name>.qcow2
agents/wnx/test-vm/upload-image.sh <dir>/<name>.qcow2 <name>.qcow2
```

in a pod with `/dev/kvm` (about 40 minutes, plus the media download and the upload),
then put the three fields the upload prints (name, sha256, Eval expiry) into
`image.bzl`. A local build takes `--work <dir>` for its ~13 GiB work disk and
`--keep-work` to keep it, with the guest's provisioning logs, after a successful build.
Unlike the tests, the build needs network access: the guest activates the Eval licence
online. The image has no Python: the pytest suites bring their own
(`//agents/modules/windows:python_test_cab`).
The media (Eval ISO, virtio-win ISO, SQL Server ISO and CU, ODBC driver) are pinned in
`bazel/extensions/test_vm_repositories.bzl`; a new SQL Server CU also bumps `MSSQL_VERSION`
in `make_image.py`.

To run the tiers against a locally built image before publishing it, point
`@win2022_core_image` at it (`--override_repository`); keep the override directory out
of `/tmp`, which linux-sandbox replaces with an empty one inside actions, so the
state action would not find the image.

## Reaching a guest

Every QEMU that `qemu_windows` starts has two sockets next to its QMP socket, in a
private directory (`/tmp/qwin.*`; the build prints the console's path at each boot),
each for one client at a time:

- `qga`, the guest agent (qemu-ga, as LocalSystem), through which the build and the
  tests drive the guest (`qemu_windows/guest.py`);
- `console`, COM1, with Windows' Special Administration Console (SAC), a shell for a
  guest whose agent does not answer, also while something else drives it. `core-vm`
  logs in there.

To use the console by hand:

```
socat -,raw,echo=0,escape=0x1d UNIX-CONNECT:/tmp/qwin.XXXXXX/console
```

Enter shows the `SAC>` prompt; `cmd` opens a command prompt channel, `ch -si 1`
switches to it (Esc Tab 0 back to SAC), and it logs in as `Administrator` with an
empty domain and `PASSWORD`. Ctrl-] ends socat. SAC is up from early in the boot, its
`cmd` about a minute later (once the sacsvr service runs), and only from the
provisioning boot on: first-logon.ps1 turns EMS on for the next boot.

## Known limits

- The install boot has no channel into the guest: a Setup or first-logon.ps1 that
  hangs shows nothing but the build's 90 min deadline. The work disk of a failed build
  stays; booted again, its console and `C:\setup\first-logon.log` tell more.
- A reply of the guest agent larger than 512 KiB can be lost, without an error to the
  host: qemu-ga writes each reply in one piece, and the guest's virtio-serial driver
  (vioser, virtio-win 0.1.302) copies a write into one non-paged pool buffer, which it
  must map in at most 128 runs of physical memory. How large a write still gets
  through depends on how fragmented that pool is (some MiB right after boot). `Guest`
  reads files in smaller chunks, and a command with more output writes it to a file.
- The machine is fixed to `-cpu host` and IDE (PIIX) disks, which saved VM states
  inherit; moving to VirtIO devices means a new image.
