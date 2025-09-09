#!groovy

/// file: sign-cmk-distro-package.groovy

/// Signs a distribution package (.rpm, .dep, etc.) for a given edition/distribution
/// at a given git hash

def main() {
    check_job_parameters([
        ["EDITION", true],
        ["DISTRO", true],
        ["VERSION", true],
        "DISABLE_CACHE",
        // TODO: Rename to FAKE_AGENT_ARTIFACTS -> we're also faking the linux updaters now
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def version = params.VERSION;
    def disable_cache = params.DISABLE_CACHE;

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def branch_base_folder = package_helper.branch_base_folder(false);

    // FIXME
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def causes = currentBuild.getBuildCauses();
    def triggerd_by = "";
    for(cause in causes) {
        if (cause.upstreamProject != null) {
            triggerd_by += cause.upstreamProject + "/" + cause.upstreamBuild + "\n";
        }
    }
    def package_type = distro_package_type(distro);
    def package_name = "";

    def docker_tag = versioning.select_docker_tag(
        params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,  // 'branch', returns '<BRANCH>-latest'
    );

    print(
        """
        |===== CONFIGURATION ===============================
        |distro:................... │${distro}│
        |edition:.................. │${edition}│
        |cmk_version:.............. │${cmk_version}│
        |safe_branch_name:......... │${safe_branch_name}│
        |checkout_dir:............. │${checkout_dir}│
        |triggerd_by:.............. │${triggerd_by}│
        |package_type:............. │${package_type}│
        |===================================================
        """.stripMargin());

    dir("${checkout_dir}") {
        container("deb-package-signer") {
            stage("Prepare workspace") {
                versioning.configure_checkout_folder(edition, cmk_version);
            }

            stage("Install signing tools") {
                // Install "dpkg-sig" manually, not part of default Ubuntu 22.04 image, see CMK-24094
                // TODO: create an image that provides signing tools to only have to build this once.
                //       The image has then to be referenced in the pod template.
                sh("""
                    apt-get update
                    apt-get install -y dpkg-sig msitools
                """);
                println("Installed dpkg-sig manually, not part of default Ubuntu 22.04 image");
            }

            stage("Download built package") {
                single_tests.fetch_package(
                    relative_job_name: "builders/build-cmk-distro-package",
                    edition: edition,
                    distro: distro,
                    download_dir: checkout_dir,
                    bisect_comment: params.CIPARAM_BISECT_COMMENT,
                    fake_windows_artifacts: params.FAKE_WINDOWS_ARTIFACTS,
                    docker_tag: docker_tag,
                    safe_branch_name: safe_branch_name,
                    no_remove_others: true,
                );
            }

            stage("Download built Windows artifacts") {
                single_tests.fetch_package(
                    relative_job_name: "${branch_base_folder}/winagt-build",
                    edition: "",
                    distro: "",
                    download_dir: checkout_dir,
                    fake_windows_artifacts: "",
                    no_remove_others: true,
                );

                // Hardcoded paths are the dream of all devs,
                // I can't evaluate what breaks if I just adopt the test_not_rc_tag test
                sh("""
                    mv check_mk_agent.msi agents/windows/check_mk_agent.msi
                """);
            }

            stage("Get package name") {
                package_name = cmd_output("ls check-mk-${edition}-${cmk_version}*.${package_type}");
            }

            stage("Sign package") {
                package_helper.sign_package(
                    checkout_dir,
                    "${checkout_dir}/${package_name}"
                );
            }

            stage("Test package") {
                package_helper.test_package(
                    "${checkout_dir}/${package_name}",
                    distro,
                    checkout_dir,
                    checkout_dir,
                    cmk_version
                );
            }

            stage("Archive stuff") {
                show_duration("archiveArtifacts") {
                    archiveArtifacts(
                        artifacts: "*.deb, *.rpm, *.cma",
                        fingerprint: true,
                    );
                }
            }
        }
    }
}

return this;
