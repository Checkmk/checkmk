"""Wrapper that transitions an already-defined target to a different platform."""

load(":private/xcomp/transition_wrapper.bzl", _platform_transitioned_target = "platform_transitioned_target")

platform_transitioned_target = _platform_transitioned_target
