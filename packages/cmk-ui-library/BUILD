load("@aspect_rules_js//npm:defs.bzl", "npm_link_package")
load("//bazel/rules:vue_package.bzl", "vue_package")

# cmk-shared-typing's typescript definitions are bazel-generated, so they are
# linked directly rather than through the pnpm lockfile (same pattern as in
# cmk-frontend-vue). Resolved via the `*` fallback path in tsconfig.json.
npm_link_package(
    name = "node_modules/cmk-shared-typing-bzl",
    src = "//packages/cmk-shared-typing:cmk_shared_typing_ts",
    package = "cmk-shared-typing",
    visibility = ["//visibility:private"],
)

vue_package(
    name = "cmk-ui-library",
    test_deps = [
        ":node_modules/@testing-library",
        ":node_modules/msw",
        ":node_modules/vue-component-type-helpers",
        "//packages/cmk-frontend:dist",
    ],
    deps = [
        ":node_modules/@internationalized",
        ":node_modules/@types",
        ":node_modules/@vitejs",
        ":node_modules/class-variance-authority",
        ":node_modules/cmk-shared-typing-bzl",
        ":node_modules/openapi-fetch",
        ":node_modules/reka-ui",
        ":node_modules/sanitize-html",
        ":node_modules/typescript",
        ":node_modules/vite",
        ":node_modules/vue3-gettext",
    ],
)
