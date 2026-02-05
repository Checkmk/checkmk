#!groovy

/// file: test-python3-unit-all.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    // The branch-specific part must not contain dots (e.g. 2.5.0),
    // because this results in an invalid branch name.
    // The pod templates uses - instead.
    def container_safe_branch_name = safe_branch_name.replace(".", "-");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-unit-all",
            cmd: "make -C tests test-unit-all",
            container_name: "ubuntu-2404-${container_safe_branch_name}-latest",
        ]);
    }
}

return this;
