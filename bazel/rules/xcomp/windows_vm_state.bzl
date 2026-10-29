"""The saved, running state of a Windows test VM, created on the build host."""

load("//agents/wnx/test-vm:image.bzl", "WINDOWS_TEST_VM")

def _vm_resources(_os, _inputs_size):
    # Bazel only takes a top-level function here: the VM's size comes from
    # the struct, not from the rule's attributes.
    return {"cpu": WINDOWS_TEST_VM.cpus, "memory": WINDOWS_TEST_VM.claim_mb}

def _windows_vm_state_impl(ctx):
    args = ctx.actions.args()
    args.add("--qemu", ctx.file._qemu)
    args.add("--qemu-img", ctx.file._qemu_img)
    args.add("--bios", ctx.file._bios)
    args.add("--image", ctx.file.image)
    args.add("--fingerprint", ctx.file._cpu_fingerprint)
    args.add("--cpus", str(WINDOWS_TEST_VM.cpus))
    args.add("--memory-mib", str(WINDOWS_TEST_VM.memory_mib))
    args.add("--warm-up", ctx.file._warm_up)
    args.add("--wait-idle", ctx.file._wait_idle)
    args.add("--purge-standby", ctx.file._purge_standby)
    args.add("--disk", ctx.outputs.disk)
    args.add("--state", ctx.outputs.state)
    ctx.actions.run(
        executable = ctx.attr._tool[DefaultInfo].files_to_run,
        arguments = [args],
        inputs = depset(
            [
                ctx.file._qemu,
                ctx.file._qemu_img,
                ctx.file.image,
                ctx.file._cpu_fingerprint,
                ctx.file._warm_up,
                ctx.file._wait_idle,
                ctx.file._purge_standby,
            ],
            transitive = [ctx.attr._firmware.files, ctx.attr._qemu_files.files],
        ),
        outputs = [ctx.outputs.disk, ctx.outputs.state],
        mnemonic = "WindowsVmState",
        progress_message = "Booting and saving the Windows test VM %{label}",
        resource_set = _vm_resources,
        execution_requirements = {
            # Needs /dev/kvm, and the state only fits this host's CPU (the
            # fingerprint input keeps cache entries apart per CPU).
            "no-remote-exec": "1",
        },
    )
    return [DefaultInfo(files = depset([ctx.outputs.disk, ctx.outputs.state]))]

windows_vm_state = rule(
    doc = """Boots a cleanly shut down Windows test image once, waits until it has
settled and saves the running VM: a disk overlay on top of the image and the
RAM/device state (qemu_windows/state.py resumes it per test). The result is only
valid for this image, this QEMU build, this device set and size, and this host CPU.""",
    implementation = _windows_vm_state_impl,
    attrs = {
        "disk": attr.output(mandatory = True, doc = "The disk overlay (qcow2)."),
        "image": attr.label(
            mandatory = True,
            allow_single_file = [".qcow2"],
            doc = "The published test image (agents/wnx/test-vm).",
        ),
        "state": attr.output(mandatory = True, doc = "The saved VM state."),
        "_bios": attr.label(
            default = Label("@qemu_linux_x86_64//:share/qemu/bios-256k.bin"),
            allow_single_file = True,
        ),
        "_cpu_fingerprint": attr.label(
            default = Label("@qemu_host_cpu//:fingerprint"),
            allow_single_file = True,
        ),
        "_firmware": attr.label(default = Label("@qemu_linux_x86_64//:firmware")),
        "_purge_standby": attr.label(
            default = Label("//agents/wnx/test-vm:guest/purge-standby.ps1"),
            allow_single_file = True,
        ),
        "_qemu": attr.label(
            default = Label("@qemu_linux_x86_64//:bin/qemu-system-x86_64"),
            allow_single_file = True,
        ),
        "_qemu_files": attr.label(default = Label("@qemu_linux_x86_64//:qemu")),
        "_qemu_img": attr.label(
            default = Label("@qemu_linux_x86_64//:bin/qemu-img"),
            allow_single_file = True,
        ),
        "_tool": attr.label(
            default = Label("//bazel/tools/windows_vm:save-state"),
            executable = True,
            cfg = "exec",
        ),
        "_wait_idle": attr.label(
            default = Label("//agents/wnx/test-vm:guest/wait-idle.ps1"),
            allow_single_file = True,
        ),
        "_warm_up": attr.label(
            default = Label("//agents/wnx/test-vm:guest/warm-up.ps1"),
            allow_single_file = True,
        ),
    },
)
