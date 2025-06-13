#!groovy

/// file: test-shellcheck_agents.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-shellcheck",
            // SHELLCHECK_OUTPUT_ARGS="-f gcc"
            cmd: "make -C tests test-shellcheck",
            output_file: "shellcheck.txt",
        ]);

        test_jenkins_helper.analyse_issues("SHELLCHECK", "shellcheck.txt");
    }
}

return this;
