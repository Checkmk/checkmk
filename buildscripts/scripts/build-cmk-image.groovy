#!groovy

/// file: build-cmk-image.groovy

/// Build Checkmk Docker image

/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: Jammy Ubuntu 22.04, see check_mk/docker_image/Dockerfile

/* groovylint-disable MethodSize */
def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "SET_LATEST_TAG",
        "SET_BRANCH_LATEST_TAG",
        "PUSH_TO_REGISTRY",
        "PUSH_TO_REGISTRY_ONLY",
        "BUILD_IMAGE_WITHOUT_CACHE",
        "CUSTOM_CMK_BASE_IMAGE",
        "DISABLE_CACHE",
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    check_environment_variables([
        "WEB_DEPLOY_DEST",
        "WEB_DEPLOY_PORT",
        "INTERNAL_DEPLOY_DEST",
        "INTERNAL_DEPLOY_PORT",
        "NODE_NAME",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");
    def test_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def package_dir = "${checkout_dir}/download";
    def source_dir = package_dir + "/" + cmk_version_rc_aware;

    def push_to_registry = PUSH_TO_REGISTRY=='true';
    def build_image = PUSH_TO_REGISTRY_ONLY!='true';
    def fake_windows_artifacts = params.FAKE_WINDOWS_ARTIFACTS;

    def relative_job_name = "${branch_base_folder}/builders/build-cmk-distro-package";

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_name:......... │${branch_name}│
        |cmk_version:......... │${cmk_version}│
        |cmk_version_rc_aware: │${cmk_version_rc_aware}│
        |branch_version:...... │${branch_version}│
        |source_dir..........: │${source_dir}│
        |push_to_registry:.... │${push_to_registry}│
        |build_image:......... │${build_image}│
        |package_dir:......... │${package_dir}│
        |branch_base_folder:.. │${branch_base_folder}│
        |===================================================
        """.stripMargin());

    smart_stage(name: 'Prepare package directory', condition: build_image) {
        inside_container() {
            dir("${checkout_dir}") {
                cleanup_directory("${package_dir}");
            }
        }
    }

    /// In order to ensure a fixed order for stages executed in parallel,
    /// we wait an increasing amount of time (N * 100ms).
    /// Without this we end up with a capped build overview matrix in the job view (Jenkins doesn't
    /// like changing order or amount of stages, which will happen with stages started `via parallel()`
    def timeOffsetForOrder = 0;

    def stages = [
        "Build source package": {
            sleep(0.1 * timeOffsetForOrder++);
            def build_instance = null;

            smart_stage(
                name: "Build source package",
                condition: build_image,
                raiseOnError: true,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-source_tgz",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: params.EDITION,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                    ],

                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: build_instance && build_image,
                raiseOnError: true,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-source_tgz",
                    selector: specific(build_instance.getId()),
                    target: source_dir,
                    fingerprintArtifacts: true,
                )
            }
        },
        "Build Package": {
            sleep(0.1 * timeOffsetForOrder++);
            def build_instance = null;

            smart_stage(
                name: "Build Package",
                condition: build_image,
                raiseOnError: true,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-distro-package",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: params.EDITION,
                        DISTRO: "ubuntu-22.04",
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: build_instance && build_image,
                raiseOnError: true,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-distro-package",
                    selector: specific(build_instance.getId()),
                    target: source_dir,
                    fingerprintArtifacts: true,
                )
            }
        }
    ];

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    inside_container(
        args: [
            "--env HOME=/home/jenkins",
        ],
        ulimit_nofile: 1024,
        set_docker_group_id: true,
        privileged: true,
    ) {
        withCredentials([
            usernamePassword(
                credentialsId: test_helper.registry_credentials_id(EDITION),
                passwordVariable: 'DOCKER_PASSPHRASE',
                usernameVariable: 'DOCKER_USERNAME'),
            usernamePassword(
                credentialsId: 'nexus',
                passwordVariable: 'NEXUS_PASSWORD',
                usernameVariable: 'NEXUS_USERNAME'),
        ]) {
            dir("${checkout_dir}") {
                smart_stage(name: 'Build Image', condition: build_image) {
                    /// TODO: fix this:
                    /// build-cmk-container does not support the downloads dir
                    /// to have an arbitrary location, so we have to provide
                    /// `download` inside the checkout_dir
                    sh("""
                        scripts/run-uvenv python \
                        buildscripts/scripts/build-cmk-container.py \
                        --branch=${branch_name} \
                        --edition=${EDITION} \
                        --version=${cmk_version} \
                        --source_path=${source_dir} \
                        --set_latest_tag=${SET_LATEST_TAG} \
                        --set_branch_latest_tag=${SET_BRANCH_LATEST_TAG} \
                        --no_cache=${BUILD_IMAGE_WITHOUT_CACHE} \
                        --image_cmk_base=${CUSTOM_CMK_BASE_IMAGE} \
                        --action=build \
                        -vvv
                    """);

                    def filename = versioning.get_docker_artifact_name(EDITION, cmk_version);

                    stage("Create and Upload BOM") {
                        // The --user helps us so the bill-of-materials has the
                        // correct owner. The --cache-dir is necessary because the
                        // working-dir seems to be /root and we cannot write there
                        // thanks to the --user
                        sh("""docker run \
                            --rm \
                            -v ${source_dir}:/in:ro \
                            -v ${checkout_dir}:/out \
                            --user "\$(id -u):\$(id -g)" \
                            ${docker_registry_no_http}/trivy:0.61.1 \
                                --cache-dir /tmp/.cache \
                                image \
                                --format cyclonedx \
                                --output /out/bill-of-materials.json \
                                --input /in/${filename}"""
                        );

                        archiveArtifacts(
                            artifacts: "bill-of-materials.json",
                            fingerprint: true,
                        );
                        withCredentials([
                            string(
                                credentialsId: 'dtrack',
                                variable: 'DTRACK_API_KEY')
                        ]) {
                            sh('curl -X "POST" "${DTRACK_URL}/api/v1/bom"' + \
                                ' -H "Content-Type: multipart/form-data"' + \
                                ' -H "X-Api-Key: ${DTRACK_API_KEY}"' + \
                                ' -F "autoCreate=true"' + \
                                ' -F "projectName=Checkmk Docker Container"' + \
                                " -F \"projectVersion=${branch_version}\"" + \
                                ' -F "bom=@bill-of-materials.json"'
                            );
                        }
                    }

                    stage("Upload to internal registry") {
                        artifacts_helper.upload_via_rsync(
                            "${package_dir}",
                            "${cmk_version_rc_aware}",
                            "${filename}",
                            "${INTERNAL_DEPLOY_DEST}",
                            "${INTERNAL_DEPLOY_PORT}",
                        );
                    }

                    def perform_public_upload = true;
                    if (branch_name.contains("sandbox")) {
                        print("Skip uploading ${filename} due to sandbox branch");
                        perform_public_upload = false;
                    } else if ("${EDITION}" == "saas") {
                        print("Skip uploading ${filename} due to saas edition");
                        perform_public_upload = false;
                    }

                    smart_stage(
                        name: "Upload to public registry",
                        condition: perform_public_upload
                    ) {
                        artifacts_helper.upload_via_rsync(
                            "${package_dir}",
                            "${cmk_version_rc_aware}",
                            "${filename}",
                            "${WEB_DEPLOY_DEST}",
                            "${WEB_DEPLOY_PORT}",
                        );
                    }
                }

                smart_stage(name: "Load image", condition: !build_image) {
                    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
                        sh("""
                            scripts/run-uvenv python \
                            buildscripts/scripts/build-cmk-container.py \
                            --branch=${branch_name} \
                            --edition=${EDITION} \
                            --version=${cmk_version} \
                            --version_rc_aware=${cmk_version_rc_aware} \
                            --source_path=${source_dir} \
                            --action=load \
                            -vvv
                        """);
                    }
                }

                smart_stage(name: "Push images", condition: push_to_registry) {
                    sh("""
                        scripts/run-uvenv python \
                        buildscripts/scripts/build-cmk-container.py \
                        --branch=${branch_name} \
                        --edition=${EDITION} \
                        --version=${cmk_version} \
                        --source_path=${source_dir} \
                        --set_latest_tag=${SET_LATEST_TAG} \
                        --set_branch_latest_tag=${SET_BRANCH_LATEST_TAG} \
                        --no_cache=${BUILD_IMAGE_WITHOUT_CACHE} \
                        --image_cmk_base=${CUSTOM_CMK_BASE_IMAGE} \
                        --action=push \
                        -vvv
                    """);
                }
            }
        }
    }
}

return this;
