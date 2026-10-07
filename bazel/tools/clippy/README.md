# Clippy lint aspect

Vendored from `lint/rules_rust/` of
[rules_lint](https://github.com/aspect-build/rules_lint) v2.9.1
(4cc8fe1dadfdc6a766b61194eaaa82fc8e17a028), Apache-2.0.

The module `aspect_rules_lint_rules_rust` is not on BCR, and
`export-ignore` drops it from every GitHub archive.

## Local changes

- `clippy.bzl`: labels point to this package; rules_lint helpers come
  from `@aspect_rules_lint//lint:defs.bzl` (`rules_lint_export_helpers.patch`).
- `clippy.bzl`: clippy warnings set the exit code to 1, so that
  `bazel lint` fails on them (clippy runs with `-Wwarnings` and exits 0).
- `BUILD`: upstream tests removed, `no-lint` tags added.

The `.bash` and `.cjs` files are unchanged and excluded from formatting
in `.gitattributes`.

## Removal

Replace with `aspect_rules_lint_rust` once the Rust build moves from
`rules_rust` to `rules_rs`. That module already fails on warnings.
