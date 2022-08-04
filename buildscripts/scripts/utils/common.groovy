#!groovy

import groovy.json.JsonSlurperClassic;

/// throw in a function - enables expressions like
///    return foo() ?: raise("Something wrong!");
raise = { msg ->
    def exc = new Exception(msg);
    //exc = org.codehaus.groovy.runtime.StackTraceUtils.sanitize(e)
    //drop items with unknown source and drop first element of stacktrace
    exc.setStackTrace(exc.getStackTrace().findAll{ it.getFileName() }.drop(1) as StackTraceElement[]);
    throw exc;
}


// Runs provided command in a shell and returns the JSON parsed stdout output
load_json = { json_file ->
    def cmd_stdout_result = cmd_output("cat ${json_file}");
    (new groovy.json.JsonSlurperClassic()).parseText(cmd_stdout_result);
}


onWindows = (env['OS'] ?: "").toLowerCase().contains('windows');


cmd_output = { cmd ->
    try {
        return ( onWindows ?
            /// bat() conveniently adds the command to stdout, thanks.
            bat(script: cmd, returnStdout: true).trim().split("\n").tail().join("\n")
            :
            sh(script: cmd, returnStdout: true).trim());
    } catch (Exception exc) {
        print("WARNING: Executing ${cmd} returned non-zero: ${exc}");
    }
    return "";
}


cleanup_directory = { directory ->
    assert directory.startsWith(env.HOME);
    sh("rm -rf '${directory}/'*");
    sh("mkdir -p '${directory}'");
}


/// Run a block based on a global "dry run level"
/// Global level = "0" (or unset) means "run everything"
/// Global level "1" means "avoid dangerous side effects"
/// Global level "2" means "avoid dangerous side effects and long running stuff (like builds)"
LONG_RUNNING = 1;
GLOBAL_IMPACT = 2;
on_dry_run_omit = {level, title, fn ->
    if (("${global_dry_run_level}" == "0" && level <= 2) ||
        ("${global_dry_run_level}" == "1" && level <= 1) ||
        ("${global_dry_run_level}" == "2" && level <= 0)) {
        /*
        print(
            """
            |==========================================================================================
            | RUN (level=${level} DRY_RUN_LEVEL=${global_dry_run_level}): "${title}"
            |==========================================================================================
            """.stripMargin());
        // return;
        */
        return fn();
    }
    print(
        """
        ||==========================================================================================
        || OMIT(level=${level} DRY_RUN_LEVEL=${global_dry_run_level}): "${title}"
        ||==========================================================================================
        """.stripMargin());
}

shout = {msg ->
    sh("figlet -w 150 ${msg}");
}

check_job_parameters = {param_list ->
    print("""
        ||== REQUIRED JOB PARAMETERS ===============================================================
        ${param_list.collect({param ->
          if (!params.containsKey(param)) {
            raise ("Expected job parameter ${param} not defined!");
          }
          "||  ${param.padRight(32)} ${"(${params[param].getClass().name.tokenize('.').last()})".padRight(12)} = |${params[param]}|"
            }).join("\n")}
        ||==========================================================================================
        """.stripMargin());
}

check_environment_variables = {param_list ->
    println("""
        ||== USED ENVIRONMENT VARIABLES ============================================================
        ${param_list.collect({param ->
            "||  ${param.padRight(45)} = |${env[param]}|"
        }).join("\n")}
        ||==========================================================================================
        """.stripMargin());
}

assert_no_dirty_files = {repo_root ->
    dir (repo_root) {
        assert sh(script: "make -C tests/ test-find-dirty-files-in-git", returnStatus: true) == 0;
    }
}
