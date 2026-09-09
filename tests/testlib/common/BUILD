load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

# Helpers shared by every test level (and by build scripts): repository
# layout, subprocess/env utilities, version and edition handling. Must not
# depend on anything that needs a site, a container, or the GUI.
py_library(
    name = "common",
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    visibility = [
        "//buildscripts/scripts:__pkg__",
        "//non-free/packages/cmk-data-backend:__pkg__",
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:version",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-trace",
        "//tests:pkg_marker",
        requirement("beautifulsoup4"),
        requirement("pexpect"),
        requirement("psutil"),
        requirement("pyyaml"),
    ],
)
