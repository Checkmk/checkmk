load("@rules_rust//cargo:defs.bzl", "cargo_build_script")
load(
    ":build_script_flags_test.bzl",
    "build_script_flags_dbg_test",
    "build_script_flags_fastbuild_test",
    "build_script_flags_opt_test",
)

# Stand-in for the build script of any crate that compiles C, e.g. ring. Only
# ever analyzed, never built: the tests below read the env off its action.
cargo_build_script(
    name = "probe_build_script",
    srcs = ["build.rs"],
    edition = "2021",
    tags = [
        "manual",
        "nobuild",
    ],
)

build_script_flags_fastbuild_test(
    name = "build_script_flags_fastbuild_test",
    tags = ["manual"],
    target_under_test = ":probe_build_script",
)

build_script_flags_dbg_test(
    name = "build_script_flags_dbg_test",
    tags = ["manual"],
    target_under_test = ":probe_build_script",
)

build_script_flags_opt_test(
    name = "build_script_flags_opt_test",
    tags = ["manual"],
    target_under_test = ":probe_build_script",
)

test_suite(
    name = "tests",
    tags = ["manual"],
    tests = [
        ":build_script_flags_dbg_test",
        ":build_script_flags_fastbuild_test",
        ":build_script_flags_opt_test",
    ],
)
