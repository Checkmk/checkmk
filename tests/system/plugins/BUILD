load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "plugins",
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
        "//tests/system:pkg_marker",
        "//tests/testlib",
    ] + select({
        "//:gpl+nonfree_repo": [
            "//non-free/tests/testlib/system/licensing",
        ],
        "//:gpl_repo": [],
    }),
)
