#!groovy

/// file: test-shell-unit.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-shell-unit",
            cmd: "make -C tests test-unit-shell",
            output_file: "shell-unit.txt",
        ]);

        test_jenkins_helper.analyse_issues("SHELLUNIT", "shell-unit.txt");
    }
}

return this;
