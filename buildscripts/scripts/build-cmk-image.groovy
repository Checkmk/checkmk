#!groovy

/// file: build-cmk-image.groovy

/// Build Checkmk Docker image

/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: Buster / Debian 10 package


def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "SET_LATEST_TAG",
        "SET_BRANCH_LATEST_TAG",
        "PUSH_TO_REGISTRY",
        "PUSH_TO_REGISTRY_ONLY",
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

    def package_dir = "${checkout_dir}/download";
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    def branch_name = (VERSION == "daily") ? versioning.safe_branch_name(scm) : versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(branch_name, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def source_dir = package_dir + "/" + cmk_version_rc_aware
    def docker_args = "--ulimit nofile=1024:1024 --group-add=${get_docker_group_id()} -v /var/run/docker.sock:/var/run/docker.sock";

    def push_to_registry = PUSH_TO_REGISTRY=='true';
    def build_image = PUSH_TO_REGISTRY_ONLY!='true';

   print(
        """
        |===== CONFIGURATION ===============================
        |branch_name:......... │${branch_name}│
        |cmk_version_rc_aware: │${cmk_version_rc_aware}│
        |push_to_registry:.... │${push_to_registry}│
        |build_image:......... │${build_image}│
        |package_dir:......... │${package_dir}│
        |===================================================
        """.stripMargin());

    currentBuild.description = (
        """
        |Building the CMK docker image
        """.stripMargin());


    shout("build image");

    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {

        docker_image_from_alias("IMAGE_TESTING").inside("${docker_args}") {
            withCredentials([
                usernamePassword(
                    credentialsId: registry_credentials_id(EDITION),
                    passwordVariable: 'DOCKER_PASSPHRASE',
                    usernameVariable: 'DOCKER_USERNAME'),
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME')
            ]) {
                dir("${checkout_dir}") {

                    conditional_stage('Prepare package directory', build_image) {
                        cleanup_directory("${package_dir}");
                    }

                    conditional_stage('Build Image', build_image) {
                        on_dry_run_omit(LONG_RUNNING, "Download build sources") {
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
                        }

                        on_dry_run_omit(LONG_RUNNING, "Run build-cmk-container.sh") {
                            /// TODO: fix this:
                            /// build-cmk-container does not support the downloads dir
                            /// to have an arbitrary location, so we have to provide
                            /// `download` inside the checkout_dir
                            sh("""buildscripts/scripts/build-cmk-container.sh \
                                ${branch_name} ${EDITION} ${cmk_version} \
                                ${source_dir} ${SET_LATEST_TAG} ${SET_BRANCH_LATEST_TAG} \
                                build""");
                        }

                        def filename = versioning.get_docker_artifact_name(EDITION, cmk_version);
                        on_dry_run_omit(LONG_RUNNING, "Upload ${filename}") {
                            stage("Upload ${filename}") {
                                artifacts_helper.upload_via_rsync(
                                    "${package_dir}",
                                    "${cmk_version_rc_aware}",
                                    "${filename}",
                                    "${INTERNAL_DEPLOY_DEST}",
                                    "${INTERNAL_DEPLOY_PORT}",
                                );
                            }
                        }

                        if (branch_name.contains("sandbox") ) {
                            print("Skip uploading ${filename} due to sandbox branch");
                        } else {
                            stage("Upload ${filename}") {
                                artifacts_helper.upload_via_rsync(
                                    "${package_dir}",
                                    "${cmk_version_rc_aware}",
                                    "${filename}",
                                    "${WEB_DEPLOY_DEST}",
                                    "${WEB_DEPLOY_PORT}",
                                );
                            }
                        }
                    }

                    conditional_stage("Push images", push_to_registry) {
                        sh("""buildscripts/scripts/build-cmk-container.sh \
                            ${branch_name} \
                            ${EDITION} \
                            ${cmk_version} \
                            ${source_dir} \
                            ${SET_LATEST_TAG} \
                            ${SET_BRANCH_LATEST_TAG} \
                            push""");
                    }
                }
            }
        }
    }
}

def registry_credentials_id(edition) {
    switch(edition) {
        case "raw":
        case "cloud":
            return "11fb3d5f-e44e-4f33-a651-274227cc48ab"
        case "enterprise":
        case "managed":
            return "registry.checkmk.com"
        default:
            throw new Exception("Cannot provide registry credentials id for edition '${edition}'")
    }
}

return this;
