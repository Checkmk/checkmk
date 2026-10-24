# Windows test VM

The `*-qemu` test tiers run cross-built Windows payloads (watest, the regression and
integration suites, Pester, the Rust tests of cmk-agent-ctl, mk-sql and mk-oracle, the
MSI install) inside a real Windows Server 2022 VM, driven from Linux. This directory
builds that VM's image.

The image is Windows Server 2022 Datacenter Evaluation, Server Core, provisioned by
`make_image.py` and cleanly shut down. QEMU itself is `@qemu_linux_x86_64`, a static build from `third_party/qemu`, so
building the image needs `/dev/kvm` (readable and writable, e.g. through the kvm
group) but no QEMU package. The guest's user and password are fixed test values
(`USER` and `PASSWORD` in `bazel/tools/windows_vm/qemu_windows/guest.py`): the
host reaches the VM only through its own sockets (see "Reaching a guest"). The
password is baked into the image, so changing it takes a new image.

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
2. Provisioning: first-logon.ps1's result, Eval activation, an NGEN flush, a component
   store cleanup, the removal of `C:\setup` (its logs go to the build's work directory)
   and a TRIM.
3. Verification: the device set the tests use, and `guest/verify-image.ps1`.

## Building an image

```
bazel run --config=test-vm //agents/wnx/test-vm:build-core -- --out <dir>/<name>.qcow2
```

builds an image on a host with `/dev/kvm`. The Eval licence runs 180 days from the
build, and the build prints its end. It takes
`--work <dir>` for its ~13 GiB work disk and `--keep-work` to keep it, with the guest's
provisioning logs, after a successful build. Unlike the tests, the build needs network
access: the guest activates the Eval licence online. The image has no Python: the
pytest suites bring their own.
The Eval and virtio-win ISOs are pinned in `bazel/extensions/test_vm_repositories.bzl`.

## Reaching a guest

Every QEMU that `qemu_windows` starts has two sockets next to its QMP socket, in a
private directory (`/tmp/qwin.*`; the build prints the console's path at each boot),
each for one client at a time:

- `qga`, the guest agent (qemu-ga, as LocalSystem), through which the build and the
  tests drive the guest (`qemu_windows/guest.py`);
- `console`, COM1, with Windows' Special Administration Console (SAC), a shell for a
  guest whose agent does not answer, also while something else drives it.

To use the console:

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
