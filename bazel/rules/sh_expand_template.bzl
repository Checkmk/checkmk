"""Templated sh_binary target.

This macro ensures that the program wrapped in the template
is reified together with the wrapper.
"""

load("@aspect_bazel_lib//lib:expand_template.bzl", _expand_template = "expand_template")

def sh_expand_template(
        name,
        src,
        visibility,
        data = [],
        **kwargs):
    name_tp = name + "_tp"
    name_sh = name + "_sh"
    _expand_template(
        name = name_tp,
        out = name_sh,
        data = [src] + data,
        tags = ["manual"],
        visibility = ["//visibility:private"],
        **kwargs
    )
    native.sh_binary(
        name = name,
        srcs = [name_sh],
        data = [src] + data,
        visibility = visibility,
    )
