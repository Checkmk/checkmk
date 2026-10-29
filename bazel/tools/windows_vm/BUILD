load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

# Separate libraries, so that what uses one is not rebuilt when another
# changes: a saved VM state depends on the machine, the guest agent and the
# serial console login, not on how commands reach the guest's console
# session.

# The device set, the QEMU process and its QMP connection, the host CPU
# check, the setup of a program that runs a QEMU.
py_library(
    name = "machine",
    srcs = [
        "qemu_windows/__init__.py",
        "qemu_windows/errors.py",
        "qemu_windows/host_cpu.py",
        "qemu_windows/machine.py",
        "qemu_windows/process.py",
        "qemu_windows/qemu.py",
        "qemu_windows/qmp.py",
    ],
    imports = ["."],
    visibility = ["//agents/wnx/test-vm:__pkg__"],
    deps = [requirement("qemu.qmp")],
)

# Commands and files in the guest, through its agent.
py_library(
    name = "guest",
    srcs = [
        "qemu_windows/guest.py",
        "qemu_windows/qga.py",
    ],
    imports = ["."],
    visibility = ["//agents/wnx/test-vm:__pkg__"],
    deps = [":machine"],
)

# PowerShell on the serial console, through Windows' SAC.
py_library(
    name = "console",
    srcs = ["qemu_windows/console.py"],
    imports = ["."],
    visibility = ["//agents/wnx/test-vm:__pkg__"],
    deps = [":guest"],
)

# Commands in the guest's console session.
py_library(
    name = "session",
    srcs = ["qemu_windows/session.py"],
    imports = ["."],
    visibility = ["//agents/wnx/test-vm:__pkg__"],
    deps = [":guest"],
)

# Resuming a saved test VM (windows_vm_state.bzl).
py_library(
    name = "state",
    srcs = ["qemu_windows/state.py"],
    imports = ["."],
    visibility = ["//agents/wnx/test-vm:__pkg__"],
    deps = [":guest"],
)

# The windows_vm_state() action.
py_binary(
    name = "save-state",
    srcs = ["save_state.py"],
    main = "save_state.py",
    visibility = ["//bazel/rules:__pkg__"],
    deps = [
        ":console",
        ":guest",
    ],
)

# What a *-qemu test tier's runner uses (qemu_test): staging its payload,
# running it in the guest.
py_library(
    name = "tier",
    srcs = [
        "qemu_windows/stage.py",
        "qemu_windows/tier.py",
    ],
    imports = ["."],
    visibility = ["//bazel/rules:__pkg__"],
    deps = [
        ":session",
        ":state",
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/unit/*.py"]),
    deps = [
        ":console",
        ":guest",
        ":machine",
        ":session",
        ":state",
        ":tier",
    ],
)

# Real processes: fake QMP and guest agent servers, and the pinned QEMU
# itself, which runs the machine's device set without KVM (accel=qtest).
py_cmk_test(
    name = "component",
    size = "medium",
    srcs = glob(["tests/component/*.py"]),
    data = [
        "@qemu_linux_x86_64//:bin/qemu-img",
        "@qemu_linux_x86_64//:bin/qemu-system-x86_64",
        "@qemu_linux_x86_64//:firmware",
        "@qemu_linux_x86_64//:share/qemu/bios-256k.bin",
    ],
    env = {
        "QEMU": "$(rootpath @qemu_linux_x86_64//:bin/qemu-system-x86_64)",
        "QEMU_BIOS": "$(rootpath @qemu_linux_x86_64//:share/qemu/bios-256k.bin)",
        "QEMU_IMG": "$(rootpath @qemu_linux_x86_64//:bin/qemu-img)",
    },
    deps = [
        ":guest",
        ":machine",
    ],
)
