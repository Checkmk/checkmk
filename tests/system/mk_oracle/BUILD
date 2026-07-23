load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "mk_oracle",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
    ),
    imports = ["../../.."],
    deps = [
        requirement("docker"),
        requirement("pytest"),
        "//tests/system:pkg_marker",
        "//tests/testlib",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
    ],
)
