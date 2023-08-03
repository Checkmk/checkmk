#!groovy

/// file: compile-all-werks.groovy

def provide_clone(repo_name, credentials_id) {
    dir("${WORKSPACE}/${repo_name}") {
        checkout([$class: "GitSCM",
            userRemoteConfigs: [[
                credentialsId: credentials_id,
                url: "ssh://jenkins@review.lan.tribe29.com:29418/${repo_name}",
            ]],
            branches: [new hudson.plugins.git.BranchSpec("FETCH_HEAD")],
            extensions: [
                [$class: 'CloneOption',
                    // reference: "${reference_clone}",
                    timeout: 20,
            ]],
        ]);
    }
}

def main() {
    def docker_args = "${mount_reference_repo_dir}";

    print(
        """
        |===== CONFIGURATION ===============================
        |docker_args:.............. │${docker_args}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    stage("Checkout repositories") {
        provide_clone("checkmk_kube_agent", "ssh-git-gerrit-jenkins");
        provide_clone("cma", "ssh-git-gerrit-jenkins");
    }

    stage("Compile werks") {
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker_image_from_alias("IMAGE_TESTING").inside("${docker_args}") {
                dir("${checkout_dir}") {
                    sh("""
                    scripts/run-pipenv run echo build venv..
                    scripts/run-pipenv run python3 -m cmk.utils.werks collect cmk  ${checkout_dir} > cmk.json
                    scripts/run-pipenv run python3 -m cmk.utils.werks collect cma ${WORKSPACE}/cma > cma.json
                    scripts/run-pipenv run python3 -m cmk.utils.werks collect checkmk_kube_agent ${WORKSPACE}/checkmk_kube_agent > kube.json

                    # jq -s '.[0] * .[1] * .[2]' cma.json cmk.json kube.json > all_werks.json
                    # no need to install jq!!!!!
                    python3 -c 'import json, sys; print(json.dumps({k: v for f in sys.argv[1:] for k, v in json.load(open(f)).items()}, indent=4))' \
                        cmk.json \
                        cma.json \
                        kube.json \
                        > ${WORKSPACE}/all_werks.json
                    """);
                }
            }
        }
    }

    stage("Archive") {
        archiveArtifacts(
            artifacts: "all_werks.json",
            fingerprint: true,
        )
    }
}
return this;

