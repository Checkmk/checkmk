#!groovy

/// file: test-python3-unit-all.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-unit-all",
            cmd: "make -C tests test-unit-all",
            container_name: "ubuntu-2404-${safe_branch_name}-latest",
        ]);
    }
}

return this;
