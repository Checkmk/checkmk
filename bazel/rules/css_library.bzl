"""css_library: a named group of CSS/SCSS files opted in for stylelint."""

def css_library(name, tags = [], **kwargs):
    native.filegroup(
        name = name,
        tags = (tags or []) + ["stylelint"],
        **kwargs
    )
