"""vue_library: a js_library plus a stylelint filegroup of its styles.

Stylelint fails on empty input, so the filegroup exists only if there are styles.
"""

load("@aspect_rules_js//js:defs.bzl", "js_library")

_STYLE_EXTENSIONS = (".vue", ".css", ".scss")

def _vue_library_impl(name, visibility, srcs, tags, **kwargs):
    style_srcs = [src for src in srcs if src.name.endswith(_STYLE_EXTENSIONS)]
    other_srcs = [src for src in srcs if not src.name.endswith(_STYLE_EXTENSIONS)]

    if style_srcs:
        native.filegroup(
            name = name + "_styles",
            srcs = style_srcs,
            tags = (tags or []) + ["stylelint"],
        )
        other_srcs.append(":" + name + "_styles")

    js_library(
        name = name,
        srcs = other_srcs,
        tags = tags,
        visibility = visibility,
        **kwargs
    )

vue_library = macro(
    doc = "A js_library whose `.vue`, `.css` and `.scss` sources are checked by stylelint.",
    implementation = _vue_library_impl,
    inherit_attrs = js_library,
    attrs = {
        "srcs": attr.label_list(allow_files = True, configurable = False),
    },
)
