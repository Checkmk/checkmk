#!groovy

/// file: build-relay-image.groovy

/// Build Checkmk Relay image

void main() {
    check_job_parameters([
        "PUSH_TO_REGISTRY",
    ])

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy")
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy")

    def safe_branch_name = versioning.safe_branch_name()
    def branch_version = versioning.get_branch_version(checkout_dir)
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? safe_branch_name : branch_version
    def cmk_version_rc_aware = versioning.get_cmk_version(branch_name, branch_version, VERSION)
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware)

    def push_to_registry = PUSH_TO_REGISTRY == 'true'

    def artifact_directory = "${checkout_dir}/artifacts"
    def is_release_candidate = cmk_version_rc_aware.contains("-rc")

    def tarball_name = "check-mk-relay-${cmk_version}.tar"

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_name:......... │${branch_name}│
        |cmk_version:......... │${cmk_version}│
        |cmk_version_rc_aware: │${cmk_version_rc_aware}│
        |artifact_directory:.. │${artifact_directory}│
        |branch_version:...... │${branch_version}│
        |push_to_registry:.... │${push_to_registry}│
        |===================================================
        """.stripMargin())

    inside_container(
        ulimit_nofile: 1024,
        set_docker_group_id: true,
        privileged: true,
    ) {
        dir("${checkout_dir}") {
            stage(name: 'Build Image') {
                // Only build the relay with ultimate edition sources
                sh("""
                    bazel build --cmk_edition=ultimate //omd/non-free/relay:image_tar
                    mkdir -p ${artifact_directory}/${cmk_version}
                    cp \$(bazel cquery --cmk_edition=ultimate //omd/non-free/relay:image_tar --output=files) \
                        ${artifact_directory}/${cmk_version}/${tarball_name};
                """)
            }

            stage(name: 'Upload tarball to internal deploy dest') {
                artifacts_helper.upload_via_rsync(
                    "${artifact_directory}",
                    "${cmk_version_rc_aware}",
                    "${tarball_name}",
                    "${INTERNAL_DEPLOY_DEST}",
                    "${INTERNAL_DEPLOY_PORT}",
                )
            }

            smart_stage(
                name: "Upload to download server",
                condition: push_to_registry && !is_release_candidate,
            ) {
                artifacts_helper.upload_via_rsync(
                    "${artifact_directory}",
                    "${cmk_version_rc_aware}",
                    "${tarball_name}",
                    "${WEB_DEPLOY_DEST}",
                    "${WEB_DEPLOY_PORT}",
                )
            }

            smart_stage(
                name: "Push image to docker hub",
                condition: push_to_registry && !is_release_candidate,
            ) {
                withCredentials([
                    usernamePassword(
                        credentialsId: "11fb3d5f-e44e-4f33-a651-274227cc48ab",
                        passwordVariable: 'DOCKER_PASSPHRASE',
                        usernameVariable: 'DOCKER_USERNAME'),
                ]) {
                    withEnv(["DOCKER_CONFIG=${checkout_dir}/.docker"]) {
                        // DOCKER_PASSPHRASE needs special care regarding escaping, so the second sh block again uses
                        // double ticks to expand "tags"
                        sh('''
                            mkdir -p ${DOCKER_CONFIG}
                            echo "${DOCKER_PASSPHRASE}" | docker login --password-stdin -u "${DOCKER_USERNAME}"
                        ''')
                        sh("""
                            bazel run --cmk_edition=ultimate //omd/non-free/relay:image_push -- --tag ${cmk_version}
                        """)
                    }
                }
            }
        }
    }
}

return this
