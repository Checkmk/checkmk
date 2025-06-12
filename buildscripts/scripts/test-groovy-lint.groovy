#!groovy

/// file: test-groovy-lint.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-groovy-lint",
            cmd: "GROOVYLINT_OUTPUT_ARGS='-o groovy-lint.txt' make -C tests test-lint-groovy",
        ]);

        test_jenkins_helper.analyse_issues("GROOVY", "packages/cmk-frontend/groovy-lint.txt");
    }
}

return this;
