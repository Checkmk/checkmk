#!groovy

/// file: test-javascript-lint.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-lint",
            cmd: """
                truncate -s-1 scripts/check-js-lint.sh
                echo " --format checkstyle > eslint.xml" >> scripts/check-js-lint.sh
                make -C tests test-lint-js-docker
            """,
        ]);

        test_jenkins_helper.analyse_issues("ESLINT", "eslint.xml");
    }
}

return this;
