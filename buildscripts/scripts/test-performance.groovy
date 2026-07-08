#!groovy

/// file: test-performance.groovy

void main() {
    check_job_parameters([
        "DISTRO",
        "EDITION",
        "FAKE_ARTIFACTS",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def disable_cache = params.DISABLE_CACHE;
    def disable_signing = params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING;
    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    // Use the directory also used by tests/testlib/containers.py to have it find
    // the downloaded package.
    def download_dir = "package_download";
    def make_target = "test-performance-docker";
    def result_dir = "results";

    def setup_values = single_tests.common_prepare(
        version: "daily",
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    dir("${checkout_dir}") {
        stage("Prepare workspace") {
            sh("""
                rm -rf ${result_dir} ${download_dir}
                mkdir -p ${result_dir} ${download_dir}
            """);
        }

        stage("Fetch Checkmk package") {
            single_tests.fetch_package(
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                disable_cache: disable_cache,
                disable_signing: disable_signing,
                distro: distro,
                docker_tag: setup_values.docker_tag,
                download_dir: download_dir,
                edition: edition,
                fake_artifacts: fake_artifacts,
                force_build: force_build,
                safe_branch_name: setup_values.safe_branch_name,
            );
        }

        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            privileged: true,
        ) {
            test_jenkins_helper.execute_test([
                name: make_target,
                cmd: "make -C tests ${make_target}",
                // output_file: "test-performance.txt",
                container_name: "this-distro-container",

                creds_files: [
                    [credentialsId: "QA_POSTGRES_KEY_FILE", location: "${checkout_dir}/QA_POSTGRES_KEY",],
                    [credentialsId: "QA_POSTGRES_CERT_FILE", location: "${checkout_dir}/QA_POSTGRES_CERT",],
                    [credentialsId: "QA_ROOT_CERT_FILE", location: "${checkout_dir}/QA_ROOT_CERT",],
                ],
                cred_env: [
                    string(credentialsId: 'JIRA_API_TOKEN_QA_ALERTS', variable: 'QA_JIRA_API_TOKEN'),
                ],
            ]);
        }
    }

    stage("Archive / process test reports") {
        dir("${checkout_dir}/${result_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "**",
                    fingerprint: true,
                );
            }
            xunit([Custom(
                customXSL: "${checkout_dir}/buildscripts/scripts/schema/pytest-xunit.xsl",
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: "**/junit.xml",
                skipNoTestFiles: false,
                stopProcessingIfError: true
            )]);
        }
    }
}

return this;
