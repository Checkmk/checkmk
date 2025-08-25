#!groovy

/// file: common.groovy

import groovy.json.JsonSlurperClassic;

// Runs provided command in a shell and returns the JSON parsed stdout output
load_json = { json_file ->
    def cmd_stdout_result = cmd_output("cat ${json_file}");
    (new groovy.json.JsonSlurperClassic()).parseText(cmd_stdout_result);
}

cleanup_directory = { directory ->
    assert directory.startsWith(env.HOME);
    sh("rm -rf '${directory}/'*");
    sh("mkdir -p '${directory}'");
}

check_job_parameters = { param_list ->
    print("""
        ||== REQUIRED JOB PARAMETERS ===============================================================
        ${param_list.collect({param_or_tuple ->
            def (param_name, must_be_nonempty) = (param_or_tuple instanceof java.util.ArrayList) ? param_or_tuple : [param_or_tuple, false];
            if (!params.containsKey(param_name)) {
                raise ("Expected job parameter ${param_name} not defined!");
            }
            def param_value = params[param_name];
            if (must_be_nonempty && (param_value instanceof java.lang.String) && !param_value) {
                raise ("Job parameter ${param_name} is expected to be nonempty!");
            }
            "||  ${param_name.padRight(32)} ${"(${param_value.getClass().name.tokenize('.').last()})".padRight(12)} = |${param_value}|"
        }).join("\n")}
        ||==========================================================================================
        """.stripMargin());
}

check_environment_variables = { param_list ->
    println("""
        ||== USED ENVIRONMENT VARIABLES ============================================================
        ${param_list.collect({param ->
            "||  ${param.padRight(45)} = |${env[param]}|"
        }).join("\n")}
        ||==========================================================================================
        """.stripMargin());
}

assert_no_modified_lock_files = { repo_root ->
    dir (repo_root) {
        assert sh(script: "make -C tests/ test-find-modified-lock-files", returnStatus: true) == 0;
    }
}

provide_clone = { repo_name, credentials_id ->
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

withCredentialFileAtLocation = {Map args, Closure body ->
    body.resolveStrategy = Closure.OWNER_FIRST;
    body.delegate = [:];
    def cp_cmd = onWindows ? "pwsh -c cp" : "cp"
    def rm_cmd = onWindows ? "pwsh -c rm -Force" : "rm -f"

    try {
        withCredentials([file(credentialsId: args.credentialsId, variable: "SECRET_LOCATION")]) {
                cmd_output("${cp_cmd} ${SECRET_LOCATION} ${args.location}");
                body();
        }
        return true;
    } finally {
        cmd_output("${rm_cmd} ${args.location}");
    }
};
