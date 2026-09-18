load("//bazel/rules:link_shared_typing.bzl", "link_shared_typing")
load("//bazel/rules:vue_package.bzl", "vue_package")

link_shared_typing()

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
