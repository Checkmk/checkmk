#!groovy
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
    def branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(branch_name, VERSION);
    def docker_args = "--ulimit nofile=1024:1024 --group-add=${get_docker_group_id()} -v /var/run/docker.sock:/var/run/docker.sock";

    def push_to_registry = PUSH_TO_REGISTRY=='true';
    def build_image = PUSH_TO_REGISTRY_ONLY!='true';

   print(
        """
        |===== CONFIGURATION ===============================
        |branch_name:....... │${branch_name}│
        |cmk_version:....... │${cmk_version}│
        |push_to_registry:.. │${push_to_registry}│
        |build_image:....... │${build_image}│
        |package_dir:....... │${package_dir}│
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
                    credentialsId: (EDITION == "raw") ? // FIXME getCredentialsId() mergen
                        "11fb3d5f-e44e-4f33-a651-274227cc48ab" :
                        "registry.checkmk.com",
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
                                "${cmk_version}",
                                "${package_dir}/${cmk_version}",
                                "${EDITION}",
                                "buster");
                            artifacts_helper.download_source_tar(
                                "${INTERNAL_DEPLOY_DEST}",
                                "${INTERNAL_DEPLOY_PORT}",
                                "${cmk_version}",
                                "${package_dir}/${cmk_version}",
                                "${EDITION}");
                        }
                        
                        on_dry_run_omit(LONG_RUNNING, "Run build-cmk-container.sh") {
                            /// TODO: fix this:
                            /// build-cmk-container does not support the downloads dir
                            /// to have an arbitrary location, so we have to provide
                            /// `download` inside the checkout_dir
                            sh("""buildscripts/scripts/build-cmk-container.sh \
                                ${branch_name} ${EDITION} ${cmk_version} \
                                ${SET_LATEST_TAG} ${SET_BRANCH_LATEST_TAG} \
                                build""");
                        }
                        
                        def filename = versioning.get_docker_artifact_name(EDITION, cmk_version);
                        on_dry_run_omit(LONG_RUNNING, "Upload ${filename}") {
                            stage("Upload ${filename}") {
                                artifacts_helper.upload_via_rsync(
                                    "${package_dir}",
                                    "${cmk_version}",
                                    "${filename}",
                                    "${INTERNAL_DEPLOY_DEST}",
                                    "${INTERNAL_DEPLOY_PORT}",
                                );
                            }
                        }
                        
                        def image_archive_file = "check-mk-${EDITION}-docker-${cmk_version}.tar.gz";
                        if (branch_name.contains("sandbox") ) {
                            print("Skip uploading ${image_archive_file} due to sandbox branch");
                        } else {
                            stage("Upload ${image_archive_file}") {
                                artifacts_helper.upload_via_rsync(
                                    "${package_dir}",
                                    "${cmk_version}",
                                    "check-mk-${EDITION}-docker-${cmk_version}.tar.gz",
                                    "${WEB_DEPLOY_DEST}",
                                    "${WEB_DEPLOY_PORT}",
                                );
                            }
                        }
                    }

                    conditional_stage("Push images", push_to_registry) {
                        sh("""buildscripts/scripts/build-cmk-container.sh \
                            ${BRANCH} \
                            ${EDITION} \
                            ${cmk_version} \
                            ${SET_LATEST_TAG} \
                            ${SET_BRANCH_LATEST_TAG} \
                            push""");
                    }
                }
            }
        }
    }
}
return this;

