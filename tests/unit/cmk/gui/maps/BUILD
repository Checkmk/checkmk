load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "maps",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/maps"],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/openapi/spec/spec_generator",
        "//cmk/gui/sidebar",
        "//packages/cmk-livestatus-client",
        # Cross-component dep: the ticket-contract test validates a GUI-minted
        # ticket with the daemon's real validator to pin the wire format.
        "//packages/cmk-maps:backend",
        "//packages/cmk-maps:gui",
        # The map-domain REST endpoints, exercised by test_rest_api_spec.
        "//packages/cmk-maps:rest_api",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
