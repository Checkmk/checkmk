load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
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

# The SPA's daemon types are generated from this schema rather than written by
# hand, so the wire contract cannot drift from the client. The generation itself
# runs in //packages/cmk-shared-typing, where openapi-typescript is already
# wired up for the GUI's REST API; only the dump lives here, next to the app it
# describes. Build-only — not part of the wheel.
py_binary(
    name = "dump_openapi_spec",
    srcs = ["tools/dump_openapi_spec.py"],
    deps = [":backend"],
)

run_binary(
    name = "openapi_spec",
    outs = ["maps_openapi.json"],
    args = [
        "--out",
        "$(execpath maps_openapi.json)",
    ],
    tool = ":dump_openapi_spec",
    visibility = ["//packages:__subpackages__"],
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
    targets = [
        "openapi_spec",
        "wheel",
    ],
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
    libs = [
        ":backend",
        ":dump_openapi_spec",
    ],
    requirements_in = "requirements.in",
)
