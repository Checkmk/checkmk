load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "ai_features",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = ["../../.."],
    deps = [
        requirement("pytest"),
        requirement("requests"),
        "//tests/system:pkg_marker",
        "//tests/testlib",
        "//tests/testlib/common:utils",
        "//tests/testlib/pytest_helpers",
    ] + select({
        "//:gpl+nonfree_repo": [
            "//non-free/tests/testlib/system/cloud",
        ],
        "//:gpl_repo": [],
    }),
)
