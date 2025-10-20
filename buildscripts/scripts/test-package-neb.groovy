#!groovy

/// file: test-package-neb.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            test_jenkins_helper.execute_test([
                name: "test-neb",
                cmd: "GCC_TOOLCHAIN=/opt/gcc-14.2.0 packages/neb/run --clean --all",
                output_file: "neb.txt",
            ]);

            test_jenkins_helper.analyse_issues("GCC", "neb.txt");
        }
    }
}

return this;
