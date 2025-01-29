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
    ]);

    check_environment_variables([
        "WEB_DEPLOY_DEST",
        "WEB_DEPLOY_PORT",
        "INTERNAL_DEPLOY_DEST",
        "INTERNAL_DEPLOY_PORT",
        "NODE_NAME",
    ]);

    shout("load libaries");

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");
    def test_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def package_dir = "${checkout_dir}/download";
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? versioning.safe_branch_name(scm) : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def source_dir = package_dir + "/" + cmk_version_rc_aware;

    def push_to_registry = PUSH_TO_REGISTRY=='true';
    def build_image = PUSH_TO_REGISTRY_ONLY!='true';

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
        |===================================================
        """.stripMargin());

    currentBuild.description += (
        """
        |Building the CMK docker image
        """.stripMargin());

    shout("build image");

    inside_container(
        args: [
            "--env HOME=/home/jenkins",
        ],
        ulimit_nofile: 1024,
        set_docker_group_id: true,
        priviliged: true,
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
                smart_stage(name: 'Prepare package directory', condition: build_image) {
                    cleanup_directory("${package_dir}");
                }

                smart_stage(name: 'Build Image', condition: build_image) {
                    artifacts_helper.download_deb(
                        "${INTERNAL_DEPLOY_DEST}",
                        "${INTERNAL_DEPLOY_PORT}",
                        "${cmk_version_rc_aware}",
                        "${source_dir}",
                        "${EDITION}",
                        "jammy");
                    artifacts_helper.download_source_tar(
                        "${INTERNAL_DEPLOY_DEST}",
                        "${INTERNAL_DEPLOY_PORT}",
                        "${cmk_version_rc_aware}",
                        "${source_dir}",
                        "${EDITION}");

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
                        -vvvv
                    """);

                    def filename = versioning.get_docker_artifact_name(EDITION, cmk_version);
                    stage("Upload to internal registry") {
                        println("Uploading ${filename}");
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
                        println("Uploading ${filename}");
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
                            -vvvv
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
                        -vvvv
                    """);
                }
            }
        }
    }
}

return this;
