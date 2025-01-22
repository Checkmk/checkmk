#!groovy

/// file: test-update-single-f12less.groovy

def build_make_target(edition) {
    def prefix = "test-update-";
    def suffix = "-docker";
    switch(edition) {
        case 'enterprise':
            return prefix + "cee" + suffix;
        case 'cloud':
            return prefix + "cce" + suffix;
        default:
            error("The update tests are not yet enabled for edition: " + edition);
    }
}

def main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'enterprise')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-22.04')
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "EDITION",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def docker_tag = versioning.select_docker_tag(
        "",                 // 'build tag'
        safe_branch_name,   // 'branch' returns '<BRANCH>-latest'
    );

    def version = params.VERSION;
    def distro = params.DISTRO;
    def edition = params.EDITION;

    def make_target = build_make_target(edition);
    def download_dir = "package_download";

    currentBuild.description += (
        """
        |Run update tests for packages<br>
        |safe_branch_name: ${safe_branch_name}<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |cmk_version_rc_aware: ${cmk_version_rc_aware}<br>
        |docker_tag: ${docker_tag}<br>
        |edition: ${edition}<br>
        |distro: ${distro}<br>
        |make_target: ${make_target}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:...... │${safe_branch_name}│
        |branch_version:........ │${branch_version}│
        |cmk_version:........... │${cmk_version}
        |cmk_version_rc_aware:.. │${cmk_version_rc_aware}
        |branch_version:........ │${branch_version}│
        |docker_tag:............ │${docker_tag}│
        |edition:............... │${edition}│
        |distro:................ │${distro}│
        |checkout_dir:.......... │${checkout_dir}│
        |make_target:........... │${make_target}│
        |===================================================
        """.stripMargin());

    stage("Prepare workspace") {
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker_image_from_alias("IMAGE_TESTING").inside(
                "--group-add=${get_docker_group_id()} \
                --ulimit nofile=1024:1024 \
                --env HOME=/home/jenkins \
                ${mount_reference_repo_dir} \
                -v /home/jenkins/.cmk-credentials:/home/jenkins/.cmk-credentials:ro \
                -v /var/run/docker.sock:/var/run/docker.sock") {
                dir("${checkout_dir}") {
                    // Cleanup test results directory before starting the test to prevent previous
                    // runs somehow affecting the current run.
                    sh("rm -rf ${WORKSPACE}/test-results");

                    /// remove downloaded packages since they consume dozens of MiB
                    sh("""rm -rf "${checkout_dir}/${download_dir}" """);

                    // Initialize our virtual environment before parallelization
                    sh("make .venv");

                    stage("Fetch Checkmk package") {
                        upstream_build(
                            relative_job_name: "builders/build-cmk-distro-package",
                            build_params: [
                                /// currently CUSTOM_GIT_REF must match, but in the future
                                /// we should define dependency paths for build-cmk-distro-package
                                CUSTOM_GIT_REF: cmd_output("git rev-parse HEAD"),
                                EDITION: edition,
                                DISTRO: distro,
                                CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                            ],
                            build_params_no_check: [
                                CIPARAM_OVERRIDE_BUILD_NODE: build_node,
                            ],
                            dest: download_dir,
                        );
                    }
                    try {
                        stage("Run `make ${make_target}`") {
                            dir("${checkout_dir}/tests") {
                                docker.withRegistry(DOCKER_REGISTRY, "nexus") {
                                    sh("""
                                        RESULT_PATH='${WORKSPACE}/test-results/${distro}' \
                                        EDITION='${edition}' \
                                        DOCKER_TAG='${docker_tag}' \
                                        VERSION='${VERSION == "daily" ? VERSION : cmk_version}' \
                                        DISTRO='${distro}' \
                                        BRANCH='${safe_branch_name}' \
                                        make ${make_target}
                                    """);
                                }
                            }
                        }
                    } finally {
                        stage("Archive / process test reports") {
                            dir("${WORKSPACE}") {
                                show_duration("archiveArtifacts") {
                                    archiveArtifacts("test-results/**");
                                }
                                xunit([Custom(
                                    customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                                    deleteOutputFiles: true,
                                    failIfNotNew: true,
                                    pattern: "**/junit.xml",
                                    skipNoTestFiles: false,
                                    stopProcessingIfError: true
                                )]);
                            }
                        }
                    }
                }
            }
        }
    }
}

return this;
