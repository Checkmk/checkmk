load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "scripts",
    size = "small",
    srcs = [
        "test_confluence_render.py",
        "test_generate_changelog.py",
    ],
    args = [
        "$(rootpath test_confluence_render.py)",
        "$(rootpath test_generate_changelog.py)",
    ],
    data = [
        "test_confluence_render.py",
        "test_generate_changelog.py",
    ],
    deps = ["//.ide/vscode:scripts_for_test"],
)
