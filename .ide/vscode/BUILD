load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:vitest/package_json.bzl", vitest_bin = "bin")
load("@rules_python//python:defs.bzl", "py_binary")

npm_link_all_packages(name = "node_modules")

js_library(
    name = "src_ts",
    srcs = glob([
        "src/**/*.ts",
        "src/**/*.css",
    ]) + ["tsconfig.json"],
)

js_library(
    name = "test_ts",
    srcs = glob(["tests/**/*.ts"]) + [
        "tsconfig.json",
        "vitest.config.ts",
    ],
)

vitest_bin.vitest_test(
    name = "test",
    args = ["run"],
    chdir = package_name(),
    data = [
        ":node_modules/@types",
        ":src_ts",
        ":test_ts",
        "//:node_modules/vitest",
    ] + glob(["config/**"]),
)

py_binary(
    name = "update_confluence_vscode_page",
    srcs = ["scripts/update_confluence_vscode_page.py"],
)

genrule(
    name = "vsix",
    srcs = glob(
        [
            "src/**",
            "config/**",
            "icons/**",
            "docs/**",
            "scripts/**",
        ],
        exclude = [
            "node_modules/**",
            "out/**",
            "*.vsix",
        ],
    ) + [
        "package.json",
        "tsconfig.json",
        "esbuild.js",
        ".vscodeignore",
        "CLAUDE.md",
        "README.md",
        "icon.png",
        "icon.svg",
    ],
    outs = ["cmk-vscode.vsix"],
    cmd = """
        ROOT=$$PWD
        EXT_DIR=$$(dirname $(location package.json))
        cd "$$EXT_DIR"
        node esbuild.js
        npx @vscode/vsce package --no-dependencies -o cmk-vscode.vsix 2>&1
        mkdir -p $$(dirname "$$ROOT/$@")
        cp cmk-vscode.vsix "$$ROOT/$@"
    """,
    local = True,
    tags = [
        "manual",
        "no-remote",
    ],
)
