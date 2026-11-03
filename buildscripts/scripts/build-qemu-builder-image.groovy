#!groovy

/// file: build-qemu-builder-image.groovy

/// Build the toolchain image of build-qemu-from-source.groovy
/// (third_party/qemu/Dockerfile) with kaniko and push it to Harbor, next to
/// the image pinned in third_party/qemu/builder-image.txt.
///
/// Only needed to change the toolchain. Pin the reference it prints in
/// builder-image.txt; a new toolchain changes the QEMU archive, so that commit
/// also bumps its revision.
///
/// Tags are <date>-<Dockerfile blob>-b<build number> (third_party/qemu/README.md
/// tells how to find the Dockerfile): the blob, unlike a commit, survives
/// rebases and the merge. They are never reused, and the ci-qemu project
/// refuses to overwrite a tag (immutability rule).
///
/// Credentials:
///     harbor-ci-qemu -> pulls the base, pushes the builder image

void main() {
    def pinned = readFile("${checkout_dir}/third_party/qemu/builder-image.txt").trim();
    // <registry>/<project>/<name>[:<tag>]@sha256:<digest> -> <registry>/<project>/<name>
    def repository = pinned.split("@")[0].replaceAll(/:[^:\/]*$/, "");
    def registry = repository.split("/")[0];
    def digest_file = "${checkout_dir}/qemu-builder-image.digest";

    dir("${checkout_dir}") {
        def date = cmd_output("date -u +%Y-%m-%d");
        def recipe = cmd_output("git rev-parse --short=12 HEAD:third_party/qemu/Dockerfile");
        def tag = "${date}-${recipe}-b${env.BUILD_NUMBER}";
        withCredentials([
            usernamePassword(
                credentialsId: "harbor-ci-qemu",
                usernameVariable: "HARBOR_USERNAME",
                passwordVariable: "HARBOR_PASSWORD"),
        ]) {
            container("kaniko-alpine") {
                // The docker config holds the push credentials: removed on exit, as
                // the container lives as long as the pod. The base64 "auth" field
                // needs no JSON escaping of the credentials. A digest file left by
                // an earlier run must not pass for this one's.
                sh("""#!/bin/sh
                    set -e
                    trap 'rm -f /kaniko/.docker/config.json' EXIT
                    rm -f '${digest_file}'
                    auth="\$(printf '%s:%s' "\$HARBOR_USERNAME" "\$HARBOR_PASSWORD" | base64 | tr -d '\\n')"
                    printf '{"auths":{"%s":{"auth":"%s"}}}' '${registry}' "\$auth" > /kaniko/.docker/config.json
                    /kaniko/executor \
                        --dockerfile third_party/qemu/Dockerfile \
                        --context third_party/qemu \
                        --destination '${repository}:${tag}' \
                        --digest-file '${digest_file}' \
                        --push-retry 3
                """);
            }
        }
        def digest = readFile(digest_file).trim();
        if (!digest.startsWith("sha256:")) {
            error("kaniko wrote no digest for ${repository}:${tag}");
        }
        def new_pin = "${repository}:${tag}@${digest}";
        currentBuild.description = new_pin;
        echo("Pin in third_party/qemu/builder-image.txt: ${new_pin}");
    }
}

return this;
