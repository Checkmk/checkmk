#!groovy

/// file: test-python3-typing.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-mypy",
            cmd: """\
set +e
./buildscripts/scripts/bazel_mypy.sh
exit_code=\$?
set -e
mkdir -p results
bazel --run_under="cd \$PWD &&" run //buildscripts/scripts:collect_mypy -- bazel-out/k8-fastbuild/bin > results/mypy-results.xml
exit \$exit_code
            """,
            disable_hot_cache: true,
        ]);

        archiveArtifacts(
            allowEmptyArchive: false,
            artifacts: "results/mypy-results.xml",
            fingerprint: true,
        );
        test_jenkins_helper.analyse_issues("JUNIT", "results/mypy-results.xml");
    }
}

return this;
