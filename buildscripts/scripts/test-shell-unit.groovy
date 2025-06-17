#!groovy

/// file: test-shell-unit.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-shell-unit",
            cmd: "make -C tests test-unit-shell",
            output_file: "shell-unit.txt",
            container_name: "ubuntu-2404-${safe_branch_name}-latest",
        ]);

        test_jenkins_helper.analyse_issues("SHELLUNIT", "shell-unit.txt");
    }
}

return this;
