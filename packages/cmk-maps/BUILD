load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

# Pure shared domain layer (no daemon/framework deps). A top-level sibling of
# backend/gui/rest_api so cmk/maps/gui can depend on it without pulling in the
# daemon's FastAPI/uvicorn stack (mirrors cmk.dcd.protocols / cmk.liveproxyd.shared).
py_library(
    name = "shared",
    srcs = glob(["cmk/maps/shared/**/*.py"]) + ["cmk/maps/__init__.py"],
    data = ["cmk/maps/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-maps/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "backend",
    srcs = glob(["cmk/maps/backend/**/*.py"]),
    data = ["cmk/maps/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-maps/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":shared",
        "//cmk/utils",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crash:crash",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-trace",
        requirement("fastapi"),
        requirement("gunicorn"),
        requirement("httpx"),
        requirement("opentelemetry-instrumentation-fastapi"),
        requirement("pydantic"),
        requirement("starlette"),
        requirement("uvicorn"),
        requirement("uvicorn-worker"),
    ],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/maps/py.typed"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-maps",
    requires = [
        "fastapi",
        "gunicorn",
        "httpx",
        "opentelemetry-instrumentation-fastapi",
        "pydantic",
        "starlette",
        "uvicorn",
        "uvicorn-worker",
    ],
    strip_path_prefixes = ["packages/cmk-maps"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":backend",
        ":py_typed",
        ":shared",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_requirements_test(
    name = "requirements-test",
    known_unused = [
        "gunicorn",  # started by the init.d script, not imported
        "uvicorn",  # ASGI server run by gunicorn, not imported
        "uvicorn-worker",  # gunicorn worker class referenced by name, not imported
    ],
    libs = ":backend",
    requirements_in = "requirements.in",
)
