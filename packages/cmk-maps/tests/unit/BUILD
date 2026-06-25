load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "unit",
    srcs = glob(["**/*.py"]),
    # Scope collection to this package: the //packages/cmk-maps:backend dep pulls
    # bundled *_test.py from cmk.plugins / cmk.gui into runfiles, which pytest's
    # rootdir scan would otherwise collect and fail on.
    args = ["packages/cmk-maps/tests/unit"],
    # Make this dir an import root so sibling test-helper modules (e.g.
    # ``fake_connection``) resolve as top-level imports under both pytest and
    # mypy, independent of pytest's import mode.
    imports = ["."],
    deps = [
        "//packages/cmk-maps:backend",
        requirement("fastapi"),
        requirement("httpx"),
        requirement("python-multipart"),
        requirement("starlette"),
    ],
)
