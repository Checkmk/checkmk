#!groovy

/// file: trigger-build-upload-cmk-distro-package.groovy

/// Triggers a distribution package build (.rpm, .dep, etc.) for a given
/// edition/distribution at a given git hash and uploads it to the tstsbuild server

def main() {
    check_job_parameters([
        "EDITION",
        "DISTRO",
        "VERSION"
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def docker_args = "${mount_reference_repo_dir}";
    def distro = params.DISTRO;
    def edition = params.EDITION;

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def branch_name = safe_branch_name;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    // Use the directory also used by tests/testlib/containers.py to have it find
    // the downloaded package.
    def download_dir = "package_download";
    def custom_git_ref = "";
    def incremented_counter = "";

    currentBuild.description += (
        """
        |Build and upload package<br>
        |safe_branch_name: ${safe_branch_name}<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |edition: ${edition}<br>
        |distro: ${distro}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:......... │${safe_branch_name}│
        |branch_name:.............. │${branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |edition:.................. │${edition}│
        |distro:................... │${distro}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    stage("Prepare workspace") {
        docker_image_from_alias("IMAGE_TESTING").inside("${docker_args}") {
            dir("${checkout_dir}") {
                /// remove downloaded packages since they consume dozens of MiB
                sh("""rm -rf "${checkout_dir}/${download_dir}" """);

                // Initialize our virtual environment before parallelization
                sh("make .venv");

                custom_git_ref = cmd_output("git rev-parse HEAD");
                incremented_counter = cmd_output("git rev-list HEAD --count");
            }
        }
    }

    stage("Trigger package build") {
        docker_image_from_alias("IMAGE_TESTING").inside("${docker_args}") {
            dir("${checkout_dir}") {
                upstream_build(
                    relative_job_name: "builders/build-cmk-distro-package",
                    build_params: [
                        /// currently CUSTOM_GIT_REF must match, but in the future
                        /// we should define dependency paths for build-cmk-distro-package
                        CUSTOM_GIT_REF: custom_git_ref,
                        EDITION: edition,
                        DISTRO: distro,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                    ],
                    dest: download_dir,
                );
            }
        }
    }

    stage("Upload artifacts") {
        def package_name = versioning.get_package_name("${checkout_dir}/${download_dir}", distro_package_type(distro), edition, cmk_version);
        def upload_path = "${INTERNAL_DEPLOY_DEST}/testbuild/${cmk_version_rc_aware}/${edition}/${incremented_counter}-${custom_git_ref}/";

        println("package name is: ${package_name}");
        println("upload_path: ${upload_path}");

        artifacts_helper.upload_version_dir(
            "${checkout_dir}/${download_dir}/${package_name}",
            "${upload_path}",
            INTERNAL_DEPLOY_PORT,
            "",
            "--mkpath",
        );
    }
}

return this;
