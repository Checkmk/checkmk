"""css_library: a named group of style sources opted in for stylelint.

Stylelint fails on empty input, so an empty group is not opted in.
"""

def _css_library_impl(name, visibility, srcs, tags, **kwargs):
    native.filegroup(
        name = name,
        srcs = srcs,
        tags = (tags or []) + (["stylelint"] if srcs else []),
        visibility = visibility,
        **kwargs
    )

css_library = macro(
    doc = "A filegroup of style sources (CSS, SCSS, Vue SFCs) checked by stylelint.",
    implementation = _css_library_impl,
    inherit_attrs = native.filegroup,
    attrs = {
        "srcs": attr.label_list(allow_files = True, configurable = False),
    },
)
