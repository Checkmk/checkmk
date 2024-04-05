#!groovy

/// file: test-extension-compatibility.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);

    check_environment_variables([
        "DOCKER_TAG",
    ]);

    stage("Check for extension actuality") {
        dir("${checkout_dir}") {
            docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
                docker_image_from_alias("IMAGE_TESTING").inside() {
                    /* groovylint-disable LineLength */
                    sh("""
                        scripts/run-pipenv run \
                          tests/extension_compatibility/output_popular_extensions.py > /tmp/extension_compatibility.txt
                        diff -u --color \
                            tests/extension_compatibility/current_extensions_under_test.txt \
                            /tmp/extension_compatibility.txt \
                        || { cat <<HERE && false

                        You can fix the above by running:
                        scripts/run-pipenv run ./tests/extension_compatibility/output_popular_extensions.py > tests/extension_compatibility/current_extensions_under_test.txt


HERE
}
                    """);
                    /* groovylint-enable LineLength */
                }
            }
        }
    }

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: ["ubuntu-20.04"],
        EDITION: "enterprise",
        VERSION: "daily",
        DOCKER_TAG: versioning.select_docker_tag(
            branch_name,
            "",
            ""),   // FIXME was DOCKER_TAG_DEFAULT before
        MAKE_TARGET: "test-extension-compatibility-docker",
        BRANCH: branch_name,
        cmk_version: versioning.get_cmk_version(branch_name, branch_version, "daily"),
    );
}

return this;
