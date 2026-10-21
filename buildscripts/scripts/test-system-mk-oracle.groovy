#!groovy

/// file: test-system-mk-oracle.groovy

void main() {
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        ["EDITION", true],  // the testees package long edition string (e.g. 'pro')
        "TEST_FILTER",  // a filter string to select which tests to run
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "EDITION",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def build_node = params.CIPARAM_OVERRIDE_BUILD_NODE;
    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def version = params.VERSION;

    def make_target = "test-system-mk-oracle";
    def result_dir = "test-results";
    def mk_oracle_binary_path = "${checkout_dir}/mk-oracle"

    def setup_values = single_tests.common_prepare(
        version: version,
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    currentBuild.description += (
        """
        |Run update tests for packages<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |cmk_version_rc_aware: ${cmk_version_rc_aware}<br>
        |edition: ${edition}<br>
        |make_target: ${make_target}<br>
        |safe_branch_name: ${safe_branch_name}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_version:........ │${branch_version}│
        |checkout_dir:.......... │${checkout_dir}│
        |cmk_version:........... │${cmk_version}
        |cmk_version_rc_aware:.. │${cmk_version_rc_aware}
        |docker_tag:............ │${setup_values.docker_tag}│
        |edition:............... │${edition}│
        |fake_artifacts:........ │${fake_artifacts}│
        |make_target:........... │${make_target}│
        |safe_branch_name:...... │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
    if (build_node == "fips") {
        // Do not start builds on FIPS node
        println("Detected build node 'fips', switching this to 'fra'.");
        build_node = "fra";
    }

    dir("${checkout_dir}") {
        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            privileged: true,
        ) {
            stage("Build mk-oracle") {
                sh("""
                    bazel build --cmk_version=${cmk_version} //packages/mk-oracle
                    install -m 0755 \
                        \$(bazel cquery --cmk_version=${cmk_version} --output=files //packages/mk-oracle) \
                        ${mk_oracle_binary_path}
                """);
            }
            try {
                stage("Run `make ${make_target}`") {
                    dir("${checkout_dir}/tests") {
                        single_tests.run_make_target(
                            result_path: "${checkout_dir}/${result_dir}",
                            edition: edition,
                            docker_tag: setup_values.docker_tag,
                            version: setup_values.cmk_version,
                            distro: distro,
                            branch_name: setup_values.safe_branch_name,
                            make_target: make_target,
                            test_filter: params.TEST_FILTER,
                            faked_artifacts: fake_artifacts,
                            mk_oracle_binary_path: "--mk-oracle-binary-path=${mk_oracle_binary_path}",
                            // can hit 5min during the heavy chain runs (without wait time)
                            // using FoS of 3
                            timeout: 15,
                        );
                    }
                }
            } finally {
                stage("Archive / process test reports") {
                    single_tests.archive_and_process_reports(test_results: "${result_dir}/**");
                }
            }
        }
    }
}

return this;
