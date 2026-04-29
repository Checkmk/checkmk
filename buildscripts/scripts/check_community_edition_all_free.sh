#!/usr/bin/env bash
# Verify the community edition .deb contains no non-free content.
#
# Two complementary checks:
#
#   1. cquery: no non-free *target* appears in the configured dependency graph.
#      Fast; catches edition-guard violations at the Bazel target level.
#      Uses --//:repo_license=gpl to resolve select() correctly for community.
#
#   2. aquery: no non-free *source file* is an input to a packaging action.
#      Slower; catches non-free files accidentally added to non-nonfree targets
#      (a gap the cquery check cannot see, since it only looks at labels).
#      Uses --//:use_faked_artifacts=true so prebuilt binaries checked into the
#      repo appear as source-file paths rather than bazel-out paths.

set -eu -o pipefail

community_edition_targets() {
    bazel cquery \
        --cmk_edition=community \
        --//:repo_license=gpl \
        --output=label \
        'deps(//omd:deb)' 2>/dev/null
}

packaged_source_files() {
    bazel aquery \
        --cmk_edition=community \
        --//:use_faked_artifacts=true \
        --output=jsonproto \
        'mnemonic("PackageTar|CopyToDirectory|CopyDirectory|InternalCopyFile",
                  deps(//omd:deb))' 2>/dev/null |
        jq -r '
      # jsonproto encodes paths as a shared fragment tree to avoid duplication.
      # Each fragment is one path component; parentId chains them root→leaf:
      #
      #   "artifacts":     [{"id": 1, "pathFragmentId": 10},
      #                     {"id": 2, "pathFragmentId": 20}, ...]
      #   "pathFragments": [{"id": 10, "label": "foo.py",        "parentId": 11},
      #                     {"id": 11, "label": "base",          "parentId": 12},
      #                     {"id": 12, "label": "cmk"},
      #                     {"id": 20, "label": "foo.tar.zst",   "parentId": 21},
      #                     {"id": 21, "label": "omd",           "parentId": 22},
      #                     {"id": 22, "label": "bin",           "parentId": 23},
      #                     {"id": 23, "label": "bazel-out"}]
      #
      # artifact 1 → walk 10→11→12 → "cmk/base/foo.py"              (kept)
      # artifact 2 → walk 20→21→22→23 → "bazel-out/bin/omd/foo.tar" (filtered)
      ([.pathFragments[]
        | {key: (.id | tostring), value: {label: .label, parentId: (.parentId // null)}}
      ] | from_entries) as $frags |
      def path(fid):
        $frags[fid | tostring] as $f |
        if $f.parentId then (path($f.parentId) + "/" + $f.label) else $f.label end;
      [.artifacts[] | path(.pathFragmentId)] |
      map(select((startswith("bazel-out") or startswith("external/")) | not)) |
      sort | unique | .[]
    '
}

report_violations() {
    local -r description="$1" findings="$2"
    [[ -z "${findings}" ]] && return 0
    echo "ERROR: ${description}:" >&2
    echo "${findings}" >&2
    return 1
}

main() {
    local -r nonfree_re="non.?free/"
    local nonfree_targets nonfree_files rc=0
    nonfree_targets=$(community_edition_targets | grep -E "${nonfree_re}" || true)
    nonfree_files=$(packaged_source_files | grep -E "${nonfree_re}" || true)
    report_violations "non-free targets in community edition dependency graph" "${nonfree_targets}" || rc=1
    report_violations "non-free source files packaged into community edition" "${nonfree_files}" || rc=1
    exit "${rc}"
}

main "$@"
