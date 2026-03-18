#!groovy

/// file: test-github-actions.groovy

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    // The branch-specific part must not contain dots (e.g. 2.5.0),
    // because this results in an invalid branch name.
    // The pod templates uses - instead.
    def container_safe_branch_name = safe_branch_name.replace(".", "-");

    dir("${checkout_dir}") {
        stage('Prepare checkout folder') {
            versioning.delete_non_cre_files();
        }

        test_jenkins_helper.execute_test([
            name: "make test-github-actions",
            cmd: "make test-github-actions",
            container_name: "ubuntu-2404-${container_safe_branch_name}-latest",
        ]);
    }
}

return this;
