#!groovy

/// file: test-python3-typing.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-mypy-docker",
            cmd: "MYPY_ADDOPTS='--no-color-output --junit-xml mypy.xml' make -C tests test-mypy",
        ]);

        test_jenkins_helper.analyse_issues("MYPY", "mypy.xml");
    }
}

return this;
