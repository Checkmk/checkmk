"""Test tier for payloads that run inside the real-Windows QEMU guest."""

load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")
load("//agents/wnx/test-vm:image.bzl", "TEST_VM_DATA", "WINDOWS_TEST_VM", "test_vm_env")

# Stages a payload and runs it in the guest.
_TIER = "//bazel/tools/windows_vm:tier"

def _qemu_test_impl(name, visibility, src, args, data, env_inherit, timeout):
    # The runner on its own, compatible and not manual, so that `bazel lint`
    # and the repository's py-file checks see it.
    py_library(
        name = name + "_runner",
        srcs = [src],
        visibility = ["//visibility:private"],
        deps = [Label(_TIER)],
    )

    py_test(
        name = name,
        size = "large",
        timeout = timeout,
        srcs = [src],
        main = src.name,
        args = args,
        data = data + [Label(label) for label in TEST_VM_DATA],
        # What qemu_windows/tier.py needs to resume the test VM.
        env = test_vm_env(),
        env_inherit = env_inherit,
        tags = [
            # Needs /dev/kvm and a VM state created on this host.
            "manual",
            # One VM per test: its vCPUs and RAM, which set how many VMs run
            # at once, and a qemu_vm to cap them by hand
            # (--local_resources=qemu_vm=N, bazel/rc/qemu.rc).
            "resources:qemu_vm:1",
            "resources:cpu:%d" % WINDOWS_TEST_VM.cpus,
            "resources:memory:%d" % WINDOWS_TEST_VM.claim_mb,
        ],
        # Incompatible without --config=test-vm (or qemu): whole-repo
        # sweeps skip the test instead of fetching its image.
        target_compatible_with = select({
            Label("//agents/wnx/test-vm:disabled"): [Label("@platforms//:incompatible")],
            "//conditions:default": [],
        }),
        visibility = visibility,
        deps = [":" + name + "_runner"],
    )

qemu_test = macro(
    doc = """Runs a Python runner that stages a payload with qemu_windows.stage and
runs it with qemu_windows.tier, in its own real-Windows QEMU VM, resumed from the
Server Core test image's saved state; see qemu_windows/tier.py for the guest
contract.""",
    implementation = _qemu_test_impl,
    attrs = {
        "args": attr.string_list(
            doc = """Runner arguments; use $(rootpath ...) and list the referenced
targets in data.""",
            configurable = False,
        ),
        "data": attr.label_list(
            doc = "Runfiles the runner stages into the guest.",
            configurable = False,
        ),
        "env_inherit": attr.string_list(
            doc = "Host variables the runner reads.",
            configurable = False,
        ),
        "src": attr.label(
            doc = "The runner, a Python script.",
            mandatory = True,
            allow_single_file = [".py"],
            configurable = False,
        ),
        "timeout": attr.string(
            doc = """The test's Bazel timeout (--test_timeout overrides it). The payload
gets what the VM's start and the runner's own work leave of it, less
qemu_windows.tier.TEARDOWN.""",
            default = "long",
            values = ["moderate", "long", "eternal"],
            configurable = False,
        ),
    },
)
