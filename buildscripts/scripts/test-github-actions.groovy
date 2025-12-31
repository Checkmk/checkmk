#!groovy

/// file: test-github-actions.groovy

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    dir("${checkout_dir}") {
        stage('Prepare checkout folder') {
            versioning.delete_non_cre_files();
        }

        test_jenkins_helper.execute_test([
            name: "test-format",
            cmd: "EDITION=community bazel run //:format.check",
            container_name: "ubuntu-2404-${safe_branch_name}-latest",
        ]);

        test_jenkins_helper.execute_test([
            name: "test-lint",
            cmd: "EDITION=community bazel lint --fixes=false ...",
            container_name: "ubuntu-2404-${safe_branch_name}-latest",
        ]);

        test_jenkins_helper.execute_test([
            name: "test-bandit",
            cmd: "EDITION=community make -C tests test-bandit",
            container_name: "ubuntu-2404-${safe_branch_name}-latest",
        ]);

        test_jenkins_helper.execute_test([
            name: "test-unit",
            cmd: "EDITION=community make -C tests test-unit",
            container_name: "ubuntu-2404-${safe_branch_name}-latest",
        ]);
    }
}

return this;
