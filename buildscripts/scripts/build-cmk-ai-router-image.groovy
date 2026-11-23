#!groovy

/// file: build-cmk-ai-router-image.groovy

// Tests the container image of the AI Router and pushes it to the internal registry.
// The tag of the image comes from its digest, so a run with an unchanged image
// changes nothing in the registry.

void main() {
    check_environment_variables([
        "CONTAINER_REGISTRY_URL",
    ]);

    def package_targets = "//non-free/packages/cmk-ai-router/...";
    def push_target = "//non-free/packages/cmk-ai-router:image_push";
    def docker_config_folder = "${checkout_dir}/.docker";

    print(
        """
        |===== CONFIGURATION ===============================
        |checkout_dir:............. │${checkout_dir}│
        |CONTAINER_REGISTRY_URL:... │${CONTAINER_REGISTRY_URL}│
        |push_target:.............. │${push_target}│
        |===================================================
        """.stripMargin());

    dir(checkout_dir) {
        inside_container() {
            stage("Test image") {
                sh("bazel test ${package_targets}");
            }

            stage("Push image to container registry") {
                withHarborCredentials {
                    withEnv([
                        "DOCKER_CONFIG=${docker_config_folder}",
                        "REGISTRY=${CONTAINER_REGISTRY}",
                    ]) {
                        try {
                            // The shell reads the credentials from the environment, so
                            // they are not part of the command that Jenkins logs.
                            sh('''
                                mkdir -p "$DOCKER_CONFIG"
                                auth="$(printf '%s:%s' "$HARBOR_USERNAME" "$HARBOR_PASSWORD" | base64 --wrap=0)"
                                printf '{"auths":{"%s":{"auth":"%s"}}}' "$REGISTRY" "$auth" > "$DOCKER_CONFIG/config.json"
                            ''');
                            sh("bazel run ${push_target}");
                        } finally {
                            sh('rm -rf "$DOCKER_CONFIG"');
                        }
                    }
                }
            }
        }
    }
}

return this;
