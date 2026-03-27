#!/usr/bin/env bash

current_offenders() {
    local pathspecs=()
    if [ ${#paths[@]} -gt 0 ]; then
        for p in "${paths[@]}"; do
            pathspecs+=("${p}/*${ext}")
        done
    else
        pathspecs+=("*${ext}")
    fi

    comm -23 \
        <(git ls-files "${pathspecs[@]}" ":!doc/treasures/*" | sort) \
        <(
            bazel cquery '
           kind("source file", deps(kind("'"$kind"'", //...)))
       ' |
                grep --fixed-strings "$ext " |
                sed -E 's| \([^)]*\)$||; s|^//([^:]+):|\1/|' |
                sort
        )
}

known_offenders() {
    # *As a last resort*, you can temporarily pass known offenders as arguments.
    # This is deliberately inconvenient and undocumented as it is highly discouraged.
    # Rather than adding something here, you should put these files into an appropriate
    # bazel target.
    while [ "$1" == "--known-offender" ]; do
        echo "$2"
        shift 2
    done
}

main() {
    if [[ $# -lt 2 ]]; then
        echo "Usage: $0 <SUFFIX> <KIND> [--path <DIR>]... [--known-offender <FILE>]..." >&2
        exit 1
    fi

    ext="$1"
    kind="$2"
    shift 2

    paths=()
    while [ "$1" == "--path" ]; do
        paths+=("$2")
        shift 2
    done

    current=$(current_offenders)
    expected=$(known_offenders "$@" | sort)

    fixed=$(comm -13 <(echo "${current}") <(echo "${expected}"))
    broken=$(comm -23 <(echo "${current}") <(echo "${expected}"))

    if [ -n "${fixed}" ]; then
        echo "Found \"${ext}\" files declared as ${kind} but listed as exception:"
        echo "${fixed}"
    fi

    if [ -n "${broken}" ]; then
        echo "Found \"${ext}\" files not declared as ${kind}:"
        echo "${broken}"
    fi

    [ -z "${fixed}${broken}" ]
}

main "$@"
