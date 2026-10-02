"""vue_package: one macro call = one standalone Vue workspace package.

A Vue workspace package is a pnpm workspace member under `packages/` that is
consumed by other packages (e.g. cmk-frontend-vue) as a regular npm dependency
(`"<name>": "workspace:*"`). This macro stamps out everything Bazel needs for
such a package, so adding the next one is copy & paste:

    load("//bazel/rules:vue_package.bzl", "vue_package")

    vue_package(
        name = "cmk-ui-library",
        deps = [
            ":node_modules/reka-ui",
            ...
        ],
    )

Generated targets:

  * `pkg` — js_library of the package sources. This is the target
    `npm_translate_lock` links into consumers' `node_modules/<name>` for
    `workspace:*` dependencies (rules_js convention: `npm_package_target_name`
    defaults to "pkg"). Consumers therefore get cache-correct dependencies:
    their type-checks/tests rerun exactly when this package's sources change.
  * `<name>` — alias for `pkg`, for humans.
  * `node_modules/*` — per-package npm links (`npm_link_all_packages`); do NOT
    call it again in the package BUILD.
  * `type-check` / `type-check-tests` — vue-tsc over `tsconfig.json` /
    `tsconfig.test.json`.
  * `unit-test` — vitest over `tests/`.
  * `eslintrc` — the package's eslint.config.mjs (root `//:eslintrc` must
    depend on it, see CMK-33211).
  * `srcs` — plain filegroup of all package files, for non-JS consumers
    (e.g. py_test code-integrity checks).

CI needs no registration: all generated tests are plain test targets, picked
up by wildcard patterns (`//packages/...`).

Package file conventions (all at the package root):
  `package.json`, `tsconfig.json`, `tsconfig.test.json`, `env.d.ts`,
  `eslint.config.mjs`, `vite.config.ts` (vitest config),
  `tests/setup-tests.ts`, sources in arbitrary directories except `tests/`.
"""

load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:vue-tsc/package_json.bzl", vue_tsc_bin = "bin")
load("//bazel/rules:vitest_test.bzl", "vitest_test")

# Tooling that lives in the root package.json and is needed inside every
# package's type-check / vitest sandbox.
_ROOT_TOOLING = [
    "//:node_modules/@vue/compiler-dom",
    "//:node_modules/@vue/server-renderer",
    "//:node_modules/@vue/test-utils",
    "//:node_modules/jsdom",
    "//:node_modules/sass-embedded",
    "//:node_modules/vitest",
    "//:node_modules/vitest-fail-on-console",
    "//:node_modules/vue",
    "//:node_modules/vue-tsc",
]

_SRC_EXCLUDES = [
    "tests/**",
    "node_modules/**",
    "vite.config.ts",
    "vitest.shared-setup.ts",
    "eslint.config.mjs",
]

def vue_package(name, deps = [], test_deps = []):
    """Declares a standalone Vue workspace package.

    Args:
      name: the npm package name (must match `name` in package.json).
      deps: npm deps of the sources — package-local `:node_modules/*` links
        and/or other vue packages' `pkg` targets.
      test_deps: extra `:node_modules/*` links only the tests need.
    """
    npm_link_all_packages(name = "node_modules")

    # Test styles get their own stylelint filegroup so they never ship in
    # `pkg`. Empty groups stay untagged: stylelint fails on empty input.
    style_srcs = native.glob(
        [
            "**/*.vue",
            "**/*.css",
            "**/*.scss",
        ],
        allow_empty = True,
        exclude = _SRC_EXCLUDES,
    )
    native.filegroup(
        name = "_stylelint_srcs",
        srcs = style_srcs,
        tags = ["stylelint"] if style_srcs else [],
        visibility = ["//visibility:private"],
    )

    test_style_srcs = native.glob(
        [
            "tests/**/*.vue",
            "tests/**/*.css",
            "tests/**/*.scss",
        ],
        allow_empty = True,
    )
    native.filegroup(
        name = "_stylelint_test_srcs",
        srcs = test_style_srcs,
        tags = ["stylelint"] if test_style_srcs else [],
        visibility = ["//visibility:private"],
    )

    js_library(
        name = "pkg",
        srcs = native.glob(
            [
                "**/*.ts",
                "**/*.vue",
                "**/*.css",
                "**/*.scss",
                "**/*.svg",
                "**/*.png",
            ],
            allow_empty = True,
            exclude = _SRC_EXCLUDES,
        ) + [
            "package.json",
            "tsconfig.json",
            ":_stylelint_srcs",
        ] + native.glob(
            # Shared config a package may export for its siblings (present in
            # cmk-ui-library, optional elsewhere). `.d.ts` files are already covered
            # by the `**/*.ts` glob above.
            ["tsconfig.*.json"],
            allow_empty = True,
        ),
        deps = deps,
        visibility = ["//visibility:public"],
    )

    native.alias(
        name = name,
        actual = ":pkg",
        visibility = ["//visibility:public"],
    )

    js_library(
        name = "eslintrc",
        srcs = ["eslint.config.mjs"] + native.glob(
            # Shared eslint building blocks a package may export (eslint.shared.mjs).
            ["eslint.*.mjs"],
            allow_empty = True,
            exclude = ["eslint.config.mjs"],
        ),
        tags = ["no-lint"],
        visibility = ["//visibility:public"],
        deps = [":pkg"],
    )

    native.filegroup(
        name = "srcs",
        srcs = native.glob(
            ["**"],
            allow_empty = True,
            exclude = ["node_modules/**"],
        ),
        visibility = ["//visibility:public"],
    )

    vue_tsc_bin.vue_tsc_test(
        name = "type-check",
        args = [
            "-p",
            "tsconfig.json",
        ],
        chdir = native.package_name(),
        data = [":pkg"] + _ROOT_TOOLING,
        include_types = True,
    )

    _test_data = [
        ":pkg",
        ":_stylelint_test_srcs",
    ] + native.glob(
        ["tests/**/*.ts"],
        allow_empty = True,
    ) + [
        "tsconfig.test.json",
        "vite.config.ts",
    ] + _ROOT_TOOLING + test_deps

    vue_tsc_bin.vue_tsc_test(
        name = "type-check-tests",
        args = [
            "-p",
            "tsconfig.test.json",
        ],
        chdir = native.package_name(),
        data = _test_data,
        include_types = True,
    )

    vitest_test(
        name = "unit-test",
        data = _test_data,
        shard_count = 4,
    )
