load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:fastapi_openapi_spec.bzl", "fastapi_openapi_spec")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")
load("//doc/documentation:defs.bzl", "package_docs")

package_docs(
    name = "docs",
    index = "docs/arch-comp-maps.rst",
    visibility = ["//doc/documentation:__pkg__"],
)

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
    deps = [
        "//packages/cmk-ccc:hostaddress",
        requirement("pydantic"),
    ],
)

py_library(
    name = "backend",
    srcs = glob(
        ["cmk/maps/backend/**/*.py"],
        # The daemon-control entry point is a __main__ script shipped to bin/
        # (see :cmk-maps-server / :cmk-maps-server-pkg), not library code.
        exclude = ["cmk/maps/backend/server/cmk-maps-server.py"],
    ),
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
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crash:crash",
        "//packages/cmk-fastapi",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-trace",
        requirement("fastapi"),
        requirement("httpx2"),
        requirement("opentelemetry-instrumentation-fastapi"),
        requirement("pydantic"),
        requirement("starlette"),
        requirement("uvicorn"),
    ],
)

# Daemon-control entry point, run by etc/init.d/maps as `cmk-maps-server <cmd>`.
py_binary(
    name = "cmk-maps-server",
    srcs = ["cmk/maps/backend/server/cmk-maps-server.py"],
    main = "cmk/maps/backend/server/cmk-maps-server.py",
    visibility = ["//visibility:public"],
    deps = [":backend"],
)

# Ship the entry script to the site's bin/ (downstream packaging pulls this into
# the omd skel tar; mirrors cmk-wsgi's cmk-wsgi-server-pkg).
pkg_files(
    name = "cmk-maps-server-pkg",
    srcs = ["cmk/maps/backend/server/cmk-maps-server.py"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "bin",
    renames = {"cmk/maps/backend/server/cmk-maps-server.py": "cmk-maps-server"},
    visibility = ["//omd/packages/cmk-maps:__pkg__"],
)

# The SPA's daemon types are generated from this schema rather than written by
# hand, so the wire contract cannot drift from the client. The generation itself
# runs in //packages/cmk-shared-typing, where openapi-typescript is already
# wired up for the GUI's REST API; only the dump lives here, next to the app it
# describes. Build-only — not part of the wheel.
fastapi_openapi_spec(
    name = "openapi_spec",
    app = "cmk.maps.backend.app:create_app",
    visibility = ["//packages:__subpackages__"],
    deps = [":backend"],
)

# GUI integration (permissions, settings pages, config domains, session-auth AJAX
# endpoints backing the SPA). Imports cmk.gui.* internals and the shared layer;
# depends only on cmk/gui sub-targets (never //cmk/gui:app), so //cmk/gui:app
# can depend on this target without a cycle.
py_library(
    name = "gui",
    srcs = glob(["cmk/maps/gui/**/*.py"]),
    data = glob(["cmk/maps/gui/builtin_icons/*.svg"]) + [
        "cmk/maps/gui/builtin_icons/LICENSE",
        "cmk/maps/py.typed",
    ],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":shared",
        "//cmk/bi",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/bi:bi_manager",
        "//cmk/gui/form_specs",
        "//cmk/gui/global_settings",
        "//cmk/gui/graphing",
        "//cmk/gui/monitor/command",
        "//cmk/gui/pagetypes",
        "//cmk/gui/rule_specs:legacy_converter",
        "//cmk/gui/sidebar",
        "//cmk/gui/watolib:password_store",
        "//cmk/utils",
        "//cmk/utils:unixsocket_http",
        "//packages/cmk-ccc:user",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-web/cmk/web/utils",
        requirement("defusedxml"),
    ],
)

# Versioned REST API endpoints for maps. Registered explicitly (not by
# directory discovery), so living outside cmk/gui/openapi/api_endpoints is fine.
py_library(
    name = "rest_api",
    srcs = glob(["cmk/maps/rest_api/**/*.py"]),
    data = ["cmk/maps/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":gui",
        ":shared",
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/oauth",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/userdb",
        "//packages/cmk-ccc:user",
        "//packages/cmk-web/cmk/web/utils",
        requirement("pydantic"),
    ],
)

# The migrations of OrbVis boards and NagVis maps, run by the update actions in
# cmk.update_config and by the cmk-migrate-maps command. The command sets up the
# GUI itself, so this target depends on //cmk/gui:app and nothing of the GUI
# may depend on it.
py_library(
    name = "migration",
    srcs = glob(["cmk/maps/migration/**/*.py"]),
    data = ["cmk/maps/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":gui",
        ":rest_api",
        ":shared",
        "//cmk/gui:app",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/userdb",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils",
        "//cmk/utils:paths",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-wsgi",
    ],
)

# The GuiFeaturePlugin cmk.gui.main_modules discovers: the only target that
# pulls in both halves of the feature, so neither half depends on the other.
py_library(
    name = "registration",
    srcs = ["cmk/maps/registration.py"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":gui",
        ":rest_api",
        "//cmk/gui_plugins/internal",
    ],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/maps/py.typed"],
)

# The icons ``cmk.maps.gui._images`` seeds into ``var/maps/images`` on page
# load. They are a filegroup and a wheel dep of their own because py_wheel
# packages only the Python sources its py_library deps carry: the ``data`` on
# ``:gui`` puts them in runfiles (so tests and a dev site see them), but not in
# the wheel an installation runs from.
filegroup(
    name = "builtin_icons",
    srcs = glob(["cmk/maps/gui/builtin_icons/*.svg"]) + [
        "cmk/maps/gui/builtin_icons/LICENSE",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-maps",
    requires = [
        "fastapi",
        "httpx2",
        "opentelemetry-instrumentation-fastapi",
        "pydantic",
        "starlette",
        "uvicorn",
    ],
    strip_path_prefixes = ["packages/cmk-maps"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":backend",
        ":builtin_icons",
        ":gui",
        ":migration",
        ":py_typed",
        ":registration",
        ":rest_api",
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
    name = "wheel_pkg",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":backend",
        ":cmk-maps-server",
        ":openapi_spec_dump",
    ],
    requirements_in = "requirements.in",
)

py_cmk_test(
    name = "unit_gui",
    size = "small",
    srcs = glob(["tests/unit_gui/**/*.py"]),
    args = ["packages/cmk-maps/tests/unit_gui"],
    use_project_pytest_config = True,
    deps = [
        ":backend",
        ":gui",
        ":rest_api",
        "//cmk/gui:core_toolkit",
        # Pins the daemon's critical states to the app's generated type.
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)
