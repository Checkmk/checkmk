#!groovy

/// file: single_tests.groovy

def common_prepare(Map args) {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, args.version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def docker_tag = versioning.select_docker_tag(
        "",                // 'build tag'
        safe_branch_name,  // 'branch', returns '<BRANCH>-latest'
    );

    currentBuild.description += (
        """
        |Run *-single-f12less test<br>
        |safe_branch_name: ${safe_branch_name}<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |cmk_version_rc_aware: ${cmk_version_rc_aware}<br>
        |docker_tag: ${docker_tag}<br>
        |edition: ${params.EDITION}<br>
        |distro: ${params.DISTRO}<br>
        |make_target: ${args.make_target}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:...... │${safe_branch_name}│
        |branch_version:........ │${branch_version}│
        |cmk_version:........... │${cmk_version}
        |cmk_version_rc_aware:.. │${cmk_version_rc_aware}
        |docker_tag:............ │${docker_tag}│
        |edition:............... │${params.EDITION}│
        |distro:................ │${params.DISTRO}│
        |checkout_dir:.......... │${checkout_dir}│
        |make_target:........... │${args.make_target}│
        |===================================================
        """.stripMargin());

    // use a map as return value to easily extend it later
    return [safe_branch_name: safe_branch_name, docker_tag: docker_tag];
}

def prepare_workspace(Map args) {
    dir("${checkout_dir}") {
        if (args.containsKey("cleanup")) {
            args["cleanup"].each { directory ->
                sh("rm -rf ${directory}");
            }
        }

        if (args.containsKey("make_venv")) {
            if (args["make_venv"]) {
                // Initialize our virtual environment before parallelization
                sh("make .venv");
            }
        }
    }
}

def fetch_package(Map args) {
    // this is a quick fix for FIPS based tests, see CMK-20851
    def build_node = params.CIPARAM_OVERRIDE_BUILD_NODE;
    if (build_node == "fips") {
        // Do not start builds on FIPS node
        println("Detected build node 'fips', switching this to 'fra'.");
        build_node = "fra"
    }

    upstream_build(
        relative_job_name: "builders/build-cmk-distro-package",
        build_params: [
            /// currently CUSTOM_GIT_REF must match, but in the future
            /// we should define dependency paths for build-cmk-distro-package
            CUSTOM_GIT_REF: cmd_output("git rev-parse HEAD"),
            EDITION: args.edition,
            DISTRO: args.distro,
            FAKE_WINDOWS_ARTIFACTS: args.fake_windows_artifacts,
        ],
        build_params_no_check: [
            CIPARAM_OVERRIDE_BUILD_NODE: build_node,
            CIPARAM_BISECT_COMMENT: args.bisect_comment,
        ],
        dest: args.download_dir,
    );
}

def run_make_target(Map args) {
    docker.withRegistry(DOCKER_REGISTRY, "nexus") {
        // no inline bash comments are allowed in this sh call
        sh("""
            RESULT_PATH='${args.result_path}' \
            EDITION='${args.edition}' \
            DOCKER_TAG='${args.docker_tag}' \
            VERSION='${args.version}' \
            DISTRO='${args.distro}' \
            BRANCH='${args.branch_name}' \
            OTEL_EXPORTER_OTLP_ENDPOINT='${env.OTEL_EXPORTER_OTLP_ENDPOINT}' \
            CI_NODE_NAME='${env.NODE_NAME}' \
            CI_WORKSPACE='${env.WORKSPACE}' \
            CI_JOB_NAME='${env.JOB_NAME}' \
            CI_BUILD_NUMBER='${env.BUILD_NUMBER}' \
            CI_BUILD_URL='${env.BUILD_URL}' \
            make ${args.make_target}
        """);
    }
}

def archive_and_process_reports(Map args) {
    show_duration("archiveArtifacts") {
        archiveArtifacts(args.test_results);
    }
    xunit([Custom(
        customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
        deleteOutputFiles: true,
        failIfNotNew: true,
        pattern: "**/junit.xml",
        skipNoTestFiles: false,
        stopProcessingIfError: true
    )]);
}

return this;
