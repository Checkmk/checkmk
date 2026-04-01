"""vue_library: a js_library for Vue single-file components with stylelint integration.

Vue SFCs contain embedded `<style>` blocks that stylelint should check.
This macro bundles the two concerns cleanly:

  * an internal `filegroup` of the `.vue` sources tagged for stylelint
  * a `js_library` that includes those sources alongside any additional ones
    (e.g. tsconfig) needed for TypeScript / ESLint processing

Usage:

    vue_library(
        name = "src_vue",
        srcs = glob(["src/**/*.vue"]),
        data = [":tsconfig"],
        deps = [":src_ts", "//:node_modules/vue"],
    )
"""

load("@aspect_rules_js//js:defs.bzl", "js_library")

def vue_library(name, srcs = [], data = [], tags = [], **kwargs):
    stylelint_fg = name + "_fg"

    native.filegroup(
        name = stylelint_fg,
        srcs = srcs,
        tags = (tags or []) + ["stylelint"],
        visibility = ["//visibility:private"],
    )

    js_library(
        name = name,
        srcs = [":" + stylelint_fg] + data,
        tags = tags,
        **kwargs
    )
