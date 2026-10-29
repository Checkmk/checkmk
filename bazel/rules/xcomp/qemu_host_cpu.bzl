"""The host CPU as the pinned QEMU sees it under KVM.

A saved Windows VM state (windows_vm_state.bzl) runs on -cpu host, so it only
resumes on a host that exposes the same CPU model and features. This repository
holds that model, as QEMU's full `host` model expansion, and is an input of the
state action: hosts that differ get their own cache entries, hosts that match
share one. Re-evaluated when the QEMU build, the CPU (model, features and
microcode) or the kernel (which decides the features KVM passes on) changes.
The state action and every test compare it with the host CPU
(bazel/tools/windows_vm/qemu_windows/host_cpu.py), which catches what these
watches miss: a KVM module parameter or kernel command line that changes the
features KVM passes on. The fingerprint carries the probe and the properties it
leaves out, so that both read the CPU the same way.

Never fails: `bazel cquery //...` and `query deps(//...)` fetch it on hosts
without KVM, where it holds "no-kvm: <reason>" and the state action and the tests
refuse to run (host_cpu.py, which also says when that is out of date).
"""

# Per-boot or per-node values that do not change what the guest sees.
_VOLATILE = [
    "apic-id",
    "core-id",
    "die-id",
    "memory",
    "module-id",
    "node-id",
    "socket-id",
    "thread-id",
]

_QMP = "\n".join([
    '{"execute": "qmp_capabilities"}',
    '{"execute": "query-cpu-model-expansion", "arguments": {"type": "full", "model": {"name": "host"}}}',
    '{"execute": "quit"}',
]) + "\n"

def _fingerprint(rctx, qemu):
    if rctx.execute(["sh", "-c", "test -r /dev/kvm && test -w /dev/kvm"]).return_code != 0:
        return "no-kvm: /dev/kvm was missing or not readable and writable for Bazel\n"
    result = rctx.execute(
        ["sh", "-c", 'printf %s "$1" | "$0" -machine none -accel kvm -display none -nodefaults -qmp stdio', qemu, _QMP],
        timeout = 60,
    )
    if result.return_code != 0:
        return "no-kvm: QEMU exited %d: %s\n" % (result.return_code, result.stderr.strip()[:200])
    for line in result.stdout.splitlines():
        reply = json.decode(line, default = None)
        if type(reply) != "dict" or type(reply.get("return")) != "dict":
            continue
        model = reply["return"].get("model")
        if model:
            props = model["props"]
            return json.encode_indent({
                "probe": _QMP,
                "props": {k: props[k] for k in sorted(props) if k not in _VOLATILE},
                "volatile": _VOLATILE,
            }) + "\n"
    return "no-kvm: no CPU model in QEMU's reply\n"

def _qemu_host_cpu_impl(rctx):
    qemu = rctx.path(rctx.attr.qemu)

    # Running a binary does not make it an input of the repository: watch it,
    # so a new QEMU build re-evaluates the fingerprint.
    rctx.watch(qemu)

    # Watched whether or not they exist: hosts without the microcode file
    # (some VMs and containers) re-evaluate once it appears. modalias names
    # the CPU's vendor, family, model and features, so an output base used on
    # another CPU re-evaluates too.
    rctx.watch("/sys/devices/system/cpu/cpu0/microcode/version")
    rctx.watch("/sys/devices/system/cpu/modalias")
    rctx.watch("/proc/sys/kernel/osrelease")
    rctx.file("fingerprint", _fingerprint(rctx, qemu))
    rctx.file("BUILD.bazel", 'exports_files(["fingerprint"])\n')

qemu_host_cpu = repository_rule(
    implementation = _qemu_host_cpu_impl,
    attrs = {
        "qemu": attr.label(
            default = Label("@qemu_linux_x86_64//:bin/qemu-system-x86_64"),
            allow_single_file = True,
        ),
    },
    # Not local = True, which re-runs it on every Bazel server start: the
    # watches above say when the answer can change.
)
