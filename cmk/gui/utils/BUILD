load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

# The three targets are layers interleaved with the foundational //cmk/gui
# buckets: //cmk/gui:core_toolkit sits on :base, //cmk/gui:html_toolkit and
# //cmk/gui:auth_core sit on :middle, and :utils sits on top of both.

py_library(
    name = "base",
    srcs = [
        "images.py",
        "speaklater.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-web",
        requirement("pillow"),
    ],
)

py_library(
    name = "middle",
    srcs = [
        "confirm_links.py",
        "dataclasses.py",
        "doc_references.py",
        "language_cookie.py",
        "misc.py",
        "mobile.py",
        "output_funnel.py",
        "popups.py",
        "roles.py",
        "security_log_events.py",
        "selection_id.py",
        "timeout_manager.py",
        "transaction_manager.py",
        "user_errors.py",
        "user_frontend_settings_cookie.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//packages/cmk-profiling:__pkg__",
        "//packages/cmk-wsgi:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/utils",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-web",
        "//packages/cmk-web/cmk/web/utils",
        requirement("flask"),
    ],
)

py_library(
    name = "utils",
    srcs = [
        "compatibility.py",
        "confirm_with_preview.py",
        "csrf_token.py",
        "encrypter.py",
        "htpasswd.py",
        "json.py",
        "labels.py",
        "loading_transition.py",
        "regex.py",
        "rendering.py",
        "request_context.py",
        "sort.py",
        "temperate_unit.py",
        "time.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//packages/cmk-profiling:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":base",
        ":middle",
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-licensing",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-ruleset-matcher",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-web/cmk/web/utils",
        requirement("flask"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":base",
        ":middle",
        ":utils",
    ],
)
