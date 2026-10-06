"""Dumps the OpenAPI schema of a FastAPI app as a build artifact."""

load("@aspect_rules_py//py:defs.bzl", "py_binary_rule")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")

def fastapi_openapi_spec(name, app, deps, visibility = None):
    """Writes the schema of `app` to `<name>.json`, with sorted keys so the bytes are stable.

    The dump runs as a build action without an OMD site, so `app` has to be a pure
    factory: building the app must not configure logging, tracing or read site state.

    Args:
      name: name of the target producing `<name>.json`
      app: the app factory as `<module>:<factory>`, called without arguments
      deps: py targets that provide the factory's module
      visibility: visibility of the generated schema target
    """
    py_binary_rule(
        name = "{}_dump".format(name),
        main = Label("//bazel/tools:dump_fastapi_openapi_spec.py"),
        deps = [Label("//bazel/tools:dump_fastapi_openapi_spec")] + deps,
    )

    out = "{}.json".format(name)
    run_binary(
        name = name,
        outs = [out],
        args = [
            "--app",
            app,
            "--out",
            "$(execpath {})".format(out),
        ],
        tool = ":{}_dump".format(name),
        visibility = visibility,
    )
