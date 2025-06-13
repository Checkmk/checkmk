#!groovy

/// file: test-shell_format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "Check shell format",
            cmd: "make -C tests test-format-shell",
        ]);
    }
}

return this;
