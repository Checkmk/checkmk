# Checkmk Docker image

## Usage

To build an image download or build a `source.tar.gz` and a checkmk package and run these commands.

See also `check_mk/buildscripts/scripts/build-cmk-image.groovy`

```bash
mkdir -p download/2024.02.19

cp ~/Downloads/check-mk-enterprise-2.5.0-2025.02.19.cee.tar.gz download/2024.02.19/
cp ~/Downloads/check-mk-enterprise-2.5.0-2025.02.19_0.jammy_amd64.deb download/2024.02.19/

scripts/run-uvenv python \
    buildscripts/scripts/build-cmk-container.py \
    --branch=master \
    --edition=enterprise \
    --version=2.5.0-2025.02.19 \
    --source_path=$PWD/download/2024.02.19 \
    --action=build \
    -vvvv
```
