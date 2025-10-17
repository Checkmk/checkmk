#!/bin/bash
# Script to verify Windows file signatures in Checkmk deb packages
#
# Prerequisites: Activate the virtual environment first:
#   source .venv/bin/activate
#
# if osslsigncode is not installed system-wide, you can build it via:
#   bazel build @osslsigncode
#
# Usage: ./verify_signing.sh <file1> [file2] [file3] ...
# Examples:
#   ./verify_signing.sh check-mk-enterprise-2.4.0p13_0.noble_amd64.deb
#   ./verify_signing.sh *.deb
#   ./verify_signing.sh check-mk-enterprise-*.deb
#   ./verify_signing.sh file1.deb file2.rpm file3.cma

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <file1> [file2] [file3] ..."
    echo "Examples:"
    echo "  $0 check-mk-enterprise-2.4.0p13_0.noble_amd64.deb"
    echo "  $0 *.deb"
    echo "  $0 check-mk-enterprise-*.deb"
    echo "  $0 file1.deb file2.rpm file3.cma"
    exit 1
fi

# Function to extract version from package filename
extract_version() {
    local pkg_file="$1"
    local basename
    basename=$(basename "$pkg_file")

    # Extract version from filename
    # DEB Format: check-mk-{edition}-{version}_{release}_{distro}_{arch}.deb
    # RPM Format: check-mk-{edition}-{version}-{release}.{distro}.{arch}.rpm
    # CMA Format: check-mk-{edition}-{version}.cma
    # TGZ Format: check-mk-{edition}-{version}.tar.gz
    # Examples:
    #   check-mk-enterprise-2.4.0p13_0.noble_amd64.deb
    #   check-mk-enterprise-2.4.0p13-1.el8.x86_64.rpm
    #   check-mk-enterprise-2.4.0p13.cma
    #   check-mk-raw-2.4.0p13.tar.gz

    # Remove extensions
    basename="${basename%.deb}"
    basename="${basename%.rpm}"
    basename="${basename%.cma}"
    basename="${basename%.tar.gz}"

    # Extract the version part (everything between edition and the first underscore/end)
    # For DEB: stop at underscore (e.g., check-mk-enterprise-2.5.0-2025.10.10_0.jammy -> 2.5.0-2025.10.10)
    # For RPM: need special handling since version ends at dash before release number
    if [[ "$pkg_file" =~ \.rpm$ ]]; then
        # RPM: check-mk-enterprise-2.4.0p13-1.el8.x86_64.rpm -> get part before -1.el8
        # Match: edition-version-release, capture version only
        if [[ "$basename" =~ check-mk-(raw|enterprise|managed|cloud|saas|free)-([0-9][^-]*)-[0-9]+\. ]]; then
            echo "${BASH_REMATCH[2]}"
            return 0
        fi
    else
        # DEB/CMA/TGZ: version can contain dashes, stops at underscore or end of string
        if [[ "$basename" =~ check-mk-(raw|enterprise|managed|cloud|saas|free)-([^_]+)$ ]] ||
            [[ "$basename" =~ check-mk-(raw|enterprise|managed|cloud|saas|free)-([^_]+)_ ]]; then
            echo "${BASH_REMATCH[2]}"
            return 0
        fi
    fi

    echo ""
    return 1
}

# Function to verify a single package file
verify_package() {
    local pkg_file="$1"

    if [ ! -f "$pkg_file" ]; then
        echo -e "${RED}ERROR: File not found: $pkg_file${NC}"
        return 1
    fi

    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Verifying: $(basename "$pkg_file")${NC}"
    echo -e "${YELLOW}========================================${NC}"

    # Extract version from filename
    local version
    version=$(extract_version "$pkg_file")

    if [ -z "$version" ]; then
        echo -e "${RED}ERROR: Could not extract version from filename: $pkg_file${NC}"
        return 1
    fi

    echo "Detected version: $version"
    echo "Package path: $pkg_file"
    echo ""

    # Get absolute path
    local abs_path
    abs_path=$(readlink -f "$pkg_file")

    # Print the pytest command
    echo "Running command:"
    echo "  env VERSION=\"$version\" PACKAGE_PATH=\"$abs_path\" pytest tests/packaging/test_files.py::test_windows_artifacts_are_signed --log-cli-level=INFO -v"
    echo ""

    # Run the pytest test
    if env VERSION="$version" PACKAGE_PATH="$abs_path" pytest tests/packaging/test_files.py::test_windows_artifacts_are_signed --log-cli-level=INFO -v; then
        echo -e "${GREEN}✓ PASSED: All signatures verified for $pkg_file${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED: Signature verification failed for $pkg_file${NC}"
        return 1
    fi
}

# Track results
total=0
passed=0
failed=0
failed_files=()

echo "Found $# file(s) to verify"
echo ""

# Process each file (shell expands globs before passing arguments)
for pkg_file in "$@"; do
    ((total++))

    if verify_package "$pkg_file"; then
        ((passed++))
    else
        ((failed++))
        failed_files+=("$pkg_file")
    fi

    echo ""
done

# Print summary
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}SUMMARY${NC}"
echo -e "${YELLOW}========================================${NC}"
echo "Total files: $total"
echo -e "${GREEN}Passed: $passed${NC}"
echo -e "${RED}Failed: $failed${NC}"

if [ $failed -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed files:${NC}"
    for file in "${failed_files[@]}"; do
        echo -e "${RED}  - $file${NC}"
    done
    exit 1
else
    echo -e "${GREEN}All signature verifications passed!${NC}"
    exit 0
fi
