#!groovy

/// file: test-neb.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            test_jenkins_helper.execute_test([
                name: "test-neb",
                cmd: "GCC_TOOLCHAIN=/opt/gcc-13.2.0 packages/neb/run --clean --all",
                output_file: "neb.txt",
            ]);

            test_jenkins_helper.analyse_issues("GCC", "neb.txt");
        }
    }
}

return this;
