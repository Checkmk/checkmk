load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_env.bzl", "bazel_env")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@mypy_requirements//:requirements.bzl", mypy_requirement = "requirement")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//bazel/tools:eslint/package_json.bzl", eslint_bin = "bin")
load("@npm//bazel/tools:npm-groovy-lint/package_json.bzl", groovy_bin = "bin")
load("@npm//bazel/tools:stylelint/package_json.bzl", stylelint_bin = "bin")
load("@rules_python//python:defs.bzl", "py_binary")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("//:bazel_variables.bzl", "UV_PIP_COMPILE_ARGS")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_stdlib_bytecode.bzl", "py_stdlib_bytecode")
load("//bazel/rules:sh_expand_template.bzl", "sh_expand_template")
load("//bazel/tools:starlark_files.bzl", "STARLARK_EXCLUDED", "STARLARK_NAMES")
load("//bazel/tools/rules_mypy/mypy:mypy.bzl", "mypy_cli")
load(":mypy_version.bzl", "MYPY_VERSION")

exports_files(
    [
        "dump_fastapi_openapi_spec.py",
        "ps_script_analyzer_wrapper.ps1",
    ],
    visibility = ["//visibility:public"],
)

# Opts the linter's own PowerShell wrapper into PSScriptAnalyzer so we eat our
# own dog food. Also satisfies //packages/cmk-repo-checks:bazel_lint_coverage,
# which requires every .ps1 in a filegroup with this tag.
filegroup(
    name = "powershell_scripts",
    srcs = ["ps_script_analyzer_wrapper.ps1"],
    tags = ["lint-with-psscriptanalyzer"],
)

npm_link_all_packages(name = "node_modules")

eslint_bin.eslint_binary(
    name = "eslint",
    data = [
        "//:node_modules/@eslint/js",
        "//:node_modules/@typescript-eslint/parser",
        "//:node_modules/@vue/eslint-config-prettier",
        "//:node_modules/@vue/eslint-config-typescript",
        "//:node_modules/eslint",
        "//:node_modules/eslint-plugin-vue",
    ],
    env = {"NODE_OPTIONS": "--max-old-space-size=8192"},
    visibility = ["//visibility:public"],
)

stylelint_bin.stylelint_binary(
    name = "stylelint",
    data = [
        ":node_modules/stylelint-config-standard",
        ":node_modules/stylelint-scss",
        "//:node_modules/postcss-html",
    ],
)

js_library(
    name = "prettierrc",
    srcs = ["prettier.config.cjs"],
    visibility = ["//:__subpackages__"],
    deps = [
        ":node_modules/@trivago/prettier-plugin-sort-imports",
    ],
)

# The hermetic JDK 17 keeps npm-groovy-lint from downloading its own JRE at
# runtime. See //bazel/tools/format:groovy-format for the full rationale.
groovy_bin.npm_groovy_lint_binary(
    name = "groovy-lint",
    data = [
        "//bazel/tools:.groovylintrc.json",
        "@remotejdk17_linux//:bin/java",
        "@remotejdk17_linux//:jdk",
    ],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath //bazel/tools:.groovylintrc.json)",
        "--javaexecutable=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath @remotejdk17_linux//:bin/java)",
    ],
    no_copy_to_bin = [
        "@remotejdk17_linux//:bin/java",
        "@remotejdk17_linux//:jdk",
    ],
)

write_file(
    name = "mypy-requirements-in",
    out = "mypy-requirements.in",
    content = ["mypy==%s" % MYPY_VERSION],
)

# Not part of //:lock_python_requirements on purpose, see mypy_version.bzl. typing-extensions is
# left out: the pydantic plugin brings the product's version, and two copies would compete.
pip_compile(
    name = "mypy_requirements",
    args = UV_PIP_COMPILE_ARGS + ["--no-emit-package=typing-extensions"],
    requirements_in = ":mypy-requirements-in",
    requirements_txt = "mypy-requirements.txt",
    tags = ["manual"],
    # for :mypy_requirements_test in the test suites of //:BUILD
    visibility = ["//:__pkg__"],
)

mypy_cli(
    name = "mypy_cli_original",
    mypy_requirement = mypy_requirement("mypy"),
    pyc_collection = "include_pyc",
    # the default Python version, like the bytecode of the standard library for :mypy_cli
    python_version = None,
    deps = [
        # for `plugins = ["pydantic.mypy"]`
        requirement("pydantic"),
    ],
)

# Bytecode for the Python tools that Bazel actions run, which otherwise compile every module they
# import in every action, the standard library included. pyc_collection adds the bytecode of their
# dependencies.
py_stdlib_bytecode(
    name = "python_stdlib_bytecode",
    visibility = [
        "//agents/modules/windows:__pkg__",
        "//bazel/rules:__pkg__",
        "//bazel/rules/private/proto:__pkg__",
        "//bazel/tools/shared_typing:__pkg__",
        "//packages/cmk-astrein:__pkg__",
        "//packages/cmk-repo-checks:__pkg__",
        "//tests/code_quality/requirements:__pkg__",
    ],
)

py_console_script_binary(
    name = "bandit",
    data = [":python_stdlib_bytecode"],
    pkg = requirement("bandit"),
    pyc_collection = "include_pyc",
    tags = [
        "manual",
        "no-mypy",
    ],
)

py_console_script_binary(
    name = "py-import-cycles",
    data = [":python_stdlib_bytecode"],
    pkg = requirement("py-import-cycles"),
    pyc_collection = "include_pyc",
    script = "py_import_cycles",
    tags = [
        "manual",
        "no-mypy",
    ],
)

# Custom mypy wrapper that filters problematic MYPYPATH entries. mypy imports from its runfiles,
# so the bytecode of the standard library goes here: mypy_cli() above takes no data.
sh_binary(
    name = "mypy_cli",
    srcs = ["mypy_wrapper.sh"],
    data = [
        ":mypy_cli_original",
        ":python_stdlib_bytecode",
    ],
)

filegroup(
    name = "clang_tidy_config",
    srcs = ["//:.clang-tidy"],
    visibility = ["//visibility:public"],
)

alias(
    name = "uv",
    actual = "@multitool//tools/uv",
    visibility = ["//visibility:public"],
)

bazel_env(
    name = "bazel_env",
    toolchains = {},
    tools = {
        "bandit": ":bandit",
        "clang-format": "@multitool_hub//tools/clang-format",
        "clang-tidy": "@multitool_hub//tools/clang-tidy",
        "genhtml": "@lcov//:genhtml",
        "lcov": "@lcov//:lcov",
        "msibuild": "@msitools//:msibuild",
        "msiinfo": "@msitools//:msiinfo",
        "mypy": ":mypy_cli_original",
        "osslsigncode": "@osslsigncode",
        "plantuml": "@plantuml",
        "pnpm": "@pnpm",
        "psign": "@psign",
        "py_import_cycles": ":py-import-cycles",
        "stylelint": ":stylelint",
        "uv": "@multitool//tools/uv",
        "winvm": "//agents/wnx/test-vm:winvm",
    },
)

py_library(
    name = "dump_fastapi_openapi_spec",
    srcs = ["dump_fastapi_openapi_spec.py"],
    visibility = ["//visibility:public"],
    deps = [requirement("openapi-spec-validator")],
)

py_binary(
    name = "extract_os_packages",
    srcs = ["extract_os_packages.py"],
    data = [":python_stdlib_bytecode"],
    main = "extract_os_packages.py",
    visibility = ["//visibility:public"],
)

[
    sh_expand_template(
        name = name,
        src = "@buildifier_prebuilt//:buildifier",
        data = ["//:buildifier_config"],
        substitutions = {
            "{buildifier_args}": args,
            "{buildifier_bin}": "$(execpath @buildifier_prebuilt//:buildifier)",
            "{config}": "$(execpath //:buildifier_config)",
        },
        template = [
            "#!/bin/bash",
            "set -e",
            'REPO_PATH="${BUILD_WORKSPACE_DIRECTORY:-.}"',
            'find "$REPO_PATH" -type f \\',
        ] + [
            '    \\! -path "${REPO_PATH}/%s" \\' % pattern
            for pattern in STARLARK_EXCLUDED
        ] + [
            "    \\( %s \\) \\" % " -o ".join(['-name "%s"' % pattern for pattern in STARLARK_NAMES]),
            '    -print | xargs "$BUILD_WORKSPACE_DIRECTORY/{buildifier_bin}" {buildifier_args} \\',
            '    -config="$BUILD_WORKSPACE_DIRECTORY/{config}" "$@"',
            "",
        ],
        visibility = ["//visibility:public"],
    )
    for name, args in [
        ("buildifier", "--lint=fix"),
        ("buildifier.check", "--lint=warn"),
    ]
]

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]),
    imports = ["."],
    deps = [
        ":dump_fastapi_openapi_spec",
        ":extract_os_packages",
        requirement("openapi-spec-validator"),
    ],
)

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = ["workspace_status.sh"],
)
