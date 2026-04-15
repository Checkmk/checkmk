load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_rules_js//js:defs.bzl", "js_binary", "js_library", "js_run_binary")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:vitest/package_json.bzl", vitest_bin = "bin")
load("@npm//.ide/vscode:@vscode/vsce/package_json.bzl", vsce_bin = "bin")
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
        "package.json",
        ":node_modules/@types",
        ":src_ts",
        ":test_ts",
        "//:node_modules/vitest",
    ] + glob(["config/**"]) + glob(
        ["changelog/**"],
        allow_empty = True,
    ),
)

py_binary(
    name = "update_confluence_vscode_page",
    srcs = ["scripts/update_confluence_vscode_page.py"],
)

py_binary(
    name = "generate_changelog",
    srcs = ["scripts/generate_changelog.py"],
)

js_binary(
    name = "esbuild_bundler",
    data = [":node_modules/esbuild"],
    entry_point = "esbuild.js",
)

js_run_binary(
    name = "bundle",
    srcs = [":src_ts"],
    chdir = package_name(),
    out_dirs = ["out"],
    tool = ":esbuild_bundler",
)

copy_to_directory(
    name = "vsix_staging",
    srcs = [
        ".vscodeignore",
        "CLAUDE.md",
        "README.md",
        "icon.png",
        "icon.svg",
        "package.json",
        ":bundle",
    ] + glob(
        [
            "config/**",
            "docs/**",
            "icons/**",
            "scripts/**",
            "changelog/**",
        ],
        allow_empty = True,
    ),
    root_paths = [package_name()],
)

vsce_bin.vsce(
    name = "vsix",
    srcs = [":vsix_staging"],
    outs = ["cmk-vscode.vsix"],
    args = [
        "package",
        "--no-dependencies",
        # Skip secretlint scan — it can't resolve its rules from the pnpm
        # node_modules layout. The extension source is public anyway.
        "--allow-package-all-secrets",
        "--allow-package-env-file",
        "-o",
        "../cmk-vscode.vsix",
    ],
    chdir = package_name() + "/vsix_staging",
)
