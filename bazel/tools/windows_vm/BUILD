load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

# Three libraries, so that what uses one is not rebuilt when another changes:
# a saved VM state depends on the machine, not on how commands reach the
# guest's console session.

# The device set, the QEMU process and its QMP connection.
py_library(
    name = "machine",
    srcs = [
        "qemu_windows/__init__.py",
        "qemu_windows/errors.py",
        "qemu_windows/machine.py",
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

# Commands in the guest's console session.
py_library(
    name = "session",
    srcs = ["qemu_windows/session.py"],
    imports = ["."],
    visibility = ["//agents/wnx/test-vm:__pkg__"],
    deps = [":guest"],
)

py_pytest_main(
    name = "__test__",
    deps = [requirement("pytest")],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/unit/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":guest",
        ":machine",
        ":session",
        requirement("pytest"),
    ],
)

# Real processes: fake QMP and guest agent servers, and the pinned QEMU
# itself, which runs the machine's device set without KVM (accel=qtest).
py_test(
    name = "component",
    size = "medium",
    srcs = glob(["tests/component/*.py"]) + [":__test__.py"],
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
    main = "__test__.py",
    deps = [
        ":__test__",
        ":guest",
        ":machine",
        requirement("pytest"),
    ],
)
