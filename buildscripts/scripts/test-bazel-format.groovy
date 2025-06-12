#!groovy

/// file: test-bazel-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-bazel-format",
            cmd: "make -C tests test-format-bazel",
            output_file: "bazel-prettier.txt",
        ]);

        test_jenkins_helper.analyse_issues("BAZELFORMAT", "bazel-prettier.txt");
    }
}

return this;
