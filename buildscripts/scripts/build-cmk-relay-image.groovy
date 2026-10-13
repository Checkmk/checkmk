#!groovy

/// file: build-relay-image.groovy

// groovylint-disable MethodSize
void main() {
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        ["DISTRO", true],
        "PUSH_TO_REGISTRY",
        ["VERSION", true],
    ])

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy")
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy")

    def safe_branch_name = versioning.safe_branch_name()
    def branch_version = versioning.get_branch_version(checkout_dir)
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (params.VERSION == "daily") ? safe_branch_name : branch_version
    def cmk_version_rc_aware = versioning.get_cmk_version(branch_name, branch_version, params.VERSION)
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware)
    def docker_tag = versioning.select_docker_tag(
        params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def distro = params.DISTRO;
    def push_to_registry = params.PUSH_TO_REGISTRY == true;

    def artifact_directory = "${checkout_dir}/artifacts"
    def docker_config_folder = "${checkout_dir}/.docker";
    def sbom_name = "check-mk-relay-${cmk_version}-bill-of-materials.json"
    def tarball_name = "check-mk-relay-${cmk_version}.tar"

    print(
        """
        |===== CONFIGURATION ===============================
        |artifact_directory:.. │${artifact_directory}│
        |branch_name:......... │${branch_name}│
        |branch_version:...... │${branch_version}│
        |cmk_version:......... │${cmk_version}│
        |cmk_version_rc_aware: │${cmk_version_rc_aware}│
        |distro:.............. │${distro}│
        |docker_tag:.......... │${docker_tag}│
        |push_to_registry:.... │${push_to_registry}│
        |===================================================
        """.stripMargin())

    inside_container(
        image: docker.image("${docker_registry_no_http}/${distro}:${docker_tag}"),
        ulimit_nofile: 1024,
        set_docker_group_id: true,
        privileged: true,
    ) {
        dir("${checkout_dir}") {
            stage("setversion") {
                versioning.set_version(cmk_version);
            }
            stage(name: 'Build Image') {
                // Only build the relay with ultimate edition sources
                sh("""
                    bazel build --cmk_edition=ultimate //omd/non-free/relay:image_tar //omd/non-free/relay:sbom
                    mkdir -p ${artifact_directory}/${cmk_version_rc_aware}
                    cp \$(bazel cquery --cmk_edition=ultimate //omd/non-free/relay:image_tar --output=files) \
                        ${artifact_directory}/${cmk_version_rc_aware}/${tarball_name}
                    cp \$(bazel cquery --cmk_edition=ultimate //omd/non-free/relay:bill_of_materials --output=files) \
                        ${artifact_directory}/${cmk_version_rc_aware}/${sbom_name}
                """)
            }

            stage(name: 'Archive SBOM') {
                archiveArtifacts(artifacts: "artifacts/${cmk_version_rc_aware}/${sbom_name}")
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

            stage(name: 'Upload to download server') {
                [tarball_name, sbom_name].each { filename ->
                    artifacts_helper.upload_via_rsync(
                        "${artifact_directory}",
                        "${cmk_version_rc_aware}",
                        "${filename}",
                        "${WEB_DEPLOY_DEST}",
                        "${WEB_DEPLOY_PORT}",
                    )
                }
            }

            smart_stage(
                name: "Push image to docker hub",
                condition: push_to_registry,
            ) {
                withCredentials([
                    usernamePassword(
                        credentialsId: "11fb3d5f-e44e-4f33-a651-274227cc48ab",
                        passwordVariable: 'DOCKER_PASSPHRASE',
                        usernameVariable: 'DOCKER_USERNAME'),
                ]) {
                    // DOCKER_PASSPHRASE needs special care regarding escaping
                    def docker_auth_encoded = "${DOCKER_USERNAME}:${DOCKER_PASSPHRASE}".bytes.encodeBase64().toString();
                    /* groovylint-disable LineLength */
                    // ''' uses system variables like $HOSTNAME, $PWD, ...
                    // """ uses groovy variables like someCustomVar
                    sh("""
                        mkdir -p ${docker_config_folder}
                        echo '{"auths":{"https://index.docker.io/v1/":{"auth":"${docker_auth_encoded}"}}}' > ${docker_config_folder}/config.json
                    """);
                    /* groovylint-enable LineLength */

                    withEnv(["DOCKER_CONFIG=${docker_config_folder}"]) {
                        sh("""
                            bazel run --cmk_edition=ultimate //omd/non-free/relay:image_push -- --tag ${cmk_version}
                        """)
                    }
                }
            }

            // RC builds are only pushed to nexus. never to dockerhub
            smart_stage(
                name: "Push image to Nexus",
                condition: push_to_registry,
            ) {
                withNexusCredentials {
                    /* groovylint-disable LineLength */
                    sh("""
                        mkdir -p ${docker_config_folder}
                        echo '{"auths":{"${docker_registry_no_http}":{"username":"${NEXUS_USERNAME}","password":"${NEXUS_PASSWORD}"}}}' > ${docker_config_folder}/config.json
                    """);
                    /* groovylint-enable LineLength */

                    withEnv(["DOCKER_CONFIG=${docker_config_folder}"]) {
                        sh("""
                            bazel run --cmk_edition=ultimate //omd/non-free/relay:image_push_nexus -- --tag ${cmk_version}
                        """)
                    }
                }
            }
        }
    }
}

return this;
