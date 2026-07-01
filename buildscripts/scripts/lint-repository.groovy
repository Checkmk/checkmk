#!groovy

/// file: lint-repository.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();
    def container_safe_branch_name = safe_branch_name.replace(".", "-");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name       : "lint-repository",
            cmd        : "scripts/lint.sh",
            output_file: "lint.log",
            container_name: "ubuntu-2404-${container_safe_branch_name}-latest",
        ]);
        archiveArtifacts(
            allowEmptyArchive: false,
            artifacts: "results.sarif",
            fingerprint: true,
        );
        test_jenkins_helper.analyse_issues("SARIF", "results.sarif");
    }
}

return this;
