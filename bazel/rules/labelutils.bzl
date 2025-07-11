# Accessors to some fields of Label
# https://bazel.build/rules/lib/builtins/Label#Label

def canonical_name(label):
    """canonical_name('@@foo//bar:baz') == 'foo'"""
    return Label(label).repo_name

def package(label):
    """package('@@repo//pkg/foo:abc') == 'pkg/foo'"""
    return Label(label).package

def workspace(label):
    """workspace('@repo//pkg/foo:abc') == 'external/repo'"""
    return Label(label).workspace_root
