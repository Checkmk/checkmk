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
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
        # Cross-component dep: the contract and built-in map tests check what the
        # GUI writes or ships with the daemon's real code.
        "//packages/cmk-maps:backend",
        "//packages/cmk-maps:gui",
        "//packages/cmk-maps:migration",
        # The map-domain REST endpoints, exercised by test_rest_api_spec.
        "//packages/cmk-maps:rest_api",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
