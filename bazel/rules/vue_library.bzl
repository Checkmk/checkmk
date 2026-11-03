"""vue_library: a vue-tsc project plus a stylelint filegroup of its styles."""

load("@aspect_rules_js//js:defs.bzl", "js_library")
load("//bazel/rules:css_library.bzl", "css_library")
load("//bazel/rules:vue_tsc.bzl", "vue_tsconfig", "vue_type_check")

_STYLE_EXTENSIONS = (".vue", ".css", ".scss")

def _vue_library_impl(name, visibility, srcs, tsconfig, tags, target_compatible_with, **kwargs):
    style_srcs = [src for src in srcs if src.name.endswith(_STYLE_EXTENSIONS)]
    other_srcs = [src for src in srcs if not src.name.endswith(_STYLE_EXTENSIONS)]

    if style_srcs:
        css_library(
            name = name + "_styles",
            srcs = style_srcs,
            tags = tags,
        )
        other_srcs.append(":" + name + "_styles")

    vue_tsconfig(
        name = name + "_tsconfig",
        src = tsconfig,
    )

    js_library(
        name = name,
        srcs = other_srcs + [":" + name + "_tsconfig"],
        tags = tags,
        visibility = visibility,
        **kwargs
    )

    vue_type_check(
        name = name + "_type_check",
        project = ":" + name,
        tags = tags,
        target_compatible_with = target_compatible_with,
    )

vue_library = macro(
    doc = "A js_library checked by stylelint in its `.vue`, `.css` and `.scss` sources and by vue-tsc, which reads linked vue packages as their declarations: a type error fails the build of `<name>_type_check`. `target_compatible_with` applies to `<name>_type_check` only.",
    implementation = _vue_library_impl,
    inherit_attrs = js_library,
    attrs = {
        "srcs": attr.label_list(allow_files = True, configurable = False),
        "tsconfig": attr.label(
            doc = "The project's tsconfig. The library named after its package directory emits declarations, so its exported types must be nameable.",
            allow_single_file = [".json"],
            configurable = False,
            mandatory = True,
        ),
    },
)
