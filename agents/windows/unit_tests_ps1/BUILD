load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "strip_prefix")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:xcomp/qemu_test.bzl", "qemu_test")

pkg_files(
    name = "pester_qemu_checkout",
    srcs = glob(["*.Tests.ps1"]) + ["//agents/windows/plugins:top_level_plugins"],
    strip_prefix = strip_prefix.from_root(),
)

pkg_files(
    name = "pester_qemu_module",
    srcs = ["@pester//:module"],
    prefix = "pester/Pester",
    strip_prefix = strip_prefix.from_pkg(),
)

pkg_files(
    name = "pester_qemu_runner",
    srcs = ["run-pester.ps1"],
)

# The suites at their checkout-relative location, the plugins where the
# suites' BeforeAll dot-sources resolve them, and the Pester module.
pkg_tar(
    name = "pester_qemu_stage",
    srcs = [
        ":pester_qemu_checkout",
        ":pester_qemu_module",
        ":pester_qemu_runner",
    ],
    extension = "tar.gz",
)

qemu_test(
    name = "pester-qemu",
    src = "pester_qemu.py",
    stage = ":pester_qemu_stage",
)
