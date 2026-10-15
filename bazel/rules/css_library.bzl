"""css_library: a named group of CSS/SCSS files opted in for stylelint."""

def _css_library_impl(name, visibility, tags, **kwargs):
    native.filegroup(
        name = name,
        tags = (tags or []) + ["stylelint"],
        visibility = visibility,
        **kwargs
    )

css_library = macro(
    doc = "A filegroup of CSS/SCSS files checked by stylelint.",
    implementation = _css_library_impl,
    inherit_attrs = native.filegroup,
)
