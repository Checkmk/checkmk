#!groovy

/// file: trigger-build-upload-cmk-distro-package.groovy

/// Triggers a distribution package build (.rpm, .dep, etc.) for a given
/// edition/distribution at a given git hash and uploads it to the tstsbuild server

def main() {
    check_job_parameters([
        "EDITION",
        "DISTRO",
        "VERSION",
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_windows_artifacts = params.FAKE_WINDOWS_ARTIFACTS;

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
    def setup_values = single_tests.common_prepare(version: "daily");

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
        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            priviliged: true,
        ) {
            single_tests.prepare_workspace(
                cleanup: [
                    "${checkout_dir}/${download_dir}"
                ],
                make_venv: true
            );
            dir("${checkout_dir}") {
                custom_git_ref = effective_git_ref;
                incremented_counter = cmd_output("git rev-list HEAD --count");
            }
        }
    }

    stage("Trigger package build") {
        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            priviliged: true,
        ) {
            dir("${checkout_dir}") {
                stage("Fetch Checkmk package") {
                    single_tests.fetch_package(
                        edition: edition,
                        distro: distro,
                        download_dir: download_dir,
                        bisect_comment: params.CIPARAM_BISECT_COMMENT,
                        fake_windows_artifacts: fake_windows_artifacts,
                    );
                }
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
