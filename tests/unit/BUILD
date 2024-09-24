load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_py//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    deps = [
        "//cmk:lib_cmk",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests:conftest",
        "//tests:testlib",
        requirement("fakeredis"),
    ],
)

py_pytest_main(
    name = "__test__",
)

write_file(
    name = "smoke_test",
    out = "test_smoke.py",
    content = [
        "def test_smoke_and_run():",
        "    assert True",
    ],
)

py_test(
    # Start the collection and load the conftests.  The complexity
    # of those warrants this target.
    name = "smoke",
    srcs = [
        ":__test__.py",
        ":smoke_test",
    ],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
    ],
    data = ["@//:pyproject.toml"],
    main = ":__test__.py",
    package_collisions = "ignore",  # "warning"
    deps = [
        ":__test__",
        ":conftest",
        "//cmk:lib_cmk",
        "//tests:conftest",
        "//tests:testlib",
    ],
)
