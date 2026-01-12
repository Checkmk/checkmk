#!groovy

/// file: tests_helper.groovy

// execute tests, catch error and output log
void execute_test(Map config = [:]) {
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    // The branch-specific part must not contain dots (e.g. 2.5.0),
    // because this results in an invalid branch name.
    // The pod templates uses - instead.
    def container_safe_branch_name = safe_branch_name.replace(".", "-")

    // update the default map content with the user provided config content
    // new key/value of provided map is automatically added to the defaultDict
    def defaultDict = [
        name: "",
        cmd: "",
        output_file: "",
        container_name: "minimal-ubuntu-checkmk-${container_safe_branch_name}",
    ] << config;

    stage("Run ${defaultDict.name}") {
        // catch any error, set stage + build result to failure,
        // but continue in order to execute the publishIssues function
        catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
            def cmd = defaultDict.cmd;
            if (defaultDict.output_file) {
                cmd += " 2>&1 | tee ${defaultDict.output_file}";
            }

            if (kubernetes_inherit_from == "UNSET") {
                run_sh_command(cmd);
            } else {
                container(defaultDict.container_name) {
                    println("'execute_test' is using k8s container '${defaultDict.container_name}'");
                    artifacts_helper.withHotCache([
                        download_dest: "~",
                        remote_download: (env.COMPRESSED_CACHE_FROM_REMOTE_DOWNLOAD == "1"),
                        remote_upload: (env.COMPRESSED_CACHE_FROM_REMOTE_UPLOAD == "1"),
                        remove_existing_cache: true,
                        target_name: defaultDict.name,
                        cache_prefix: versioning.distro_code(),
                        // When we mount the shared repository cache, we won't pack the repository cache under ~/.cache
                        // into the hot cache and therefore we dont need to consider WORKSPACE and MODULE.bazel.lock
                        files_to_consider: [
                            '.bazelversion',
                            'requirements.txt',
                            'bazel/tools/package.json',
                        ] + (env.MOUNT_SHARED_REPOSITORY_CACHE == "1" ? [] : ['WORKSPACE', 'MODULE.bazel.lock']),
                    ]) {
                        run_sh_command(cmd);
                    }
                }
            }
        }
    }
}

void run_sh_command(cmd) {
    sh("""
        set -o pipefail
        ${cmd}
    """);
}

// create issues parser
// in case 'as_stage' is set false, the parser list will be returned
// otherwise a publish issue stage is created
/* groovylint-disable MethodSize, LineLength */
Object analyse_issues(result_check_type, result_check_file_pattern, as_stage=true) {
    def issues = [];
    def parserId = '';  // used for custom groovyScript parser

    // using the same parser of scanForIssues multiple times in one Jenkins job will cause
    // java.lang.IllegalStateException: ID maven-warnings is already used by another action
    // therefore a unique name can be given to each parser to avoid this issue

    switch (result_check_type) {
        case "BAZELFORMAT":
            parserId = "bazelformat";
            update_custom_parser([
                id: parserId, // ID
                name: 'Bazel Format', // Name shown on left side menu
                regex: '(.*)\\s#\\s(reformat)$', // RegEx
                mapping: 'return builder.setFileName(matcher.group(1)).setMessage(matcher.group(2)).buildOptional()', // Mapping script
                example: "omd/packages/freetds/freetds_http.bzl # reformat",  // example log message
            //       |               1                     |  |   2   |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "BAZELLINT":
            parserId = "bazellint";
            update_custom_parser([
                id: parserId, // ID
                name: 'Bazel Lint', // Name shown on left side menu
                regex: '(.*):(\\d+):(\\d+):(.*)', // RegEx
                mapping: 'return builder.setFileName(matcher.group(1)).setMessage(matcher.group(4)).setLineStart(Integer.parseInt(matcher.group(2))).setColumnStart(Integer.parseInt(matcher.group(3))).buildOptional()', // Mapping script
                example: "omd/packages/freetds/freetds_http.bzl:8:19: syntax error near build_file",  // example log message
            //       |               1                     |2|3 |             4               |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "CLANG":
            issues.add(scanForIssues(
                tool: clang(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "CODENARC":
            issues.add(scanForIssues(
                tool: codeNarc(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "PRETTIER":
            parserId = "prettier";
            update_custom_parser([
                id: parserId, // ID
                name: 'CSS Format', // Name shown on left side menu
                regex: '^\\[warn\\]\\s(.*\\.(?:scss|css|ts|js))$', // RegEx
                mapping: 'return builder.setFileName(matcher.group(1)).buildOptional()', // Mapping script
                example: "[warn] web/htdocs/themes/facelift/scss/_bi.scss",  // example log message
            //       |      |          1                             |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "ESLINT":
            issues.add(scanForIssues(
                tool: esLint(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "GCC":
            issues.add(scanForIssues(
                tool: gcc(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "GROOVY":
            parserId = "groovy-lint";
            update_custom_parser([
                id: parserId, // ID
                name: 'Groovy Lint', // Name shown on left side menu
                regex: '(.*\\.groovy$)\\n(\\s{2})(\\d+)(\\s+)(\\w+)(\\s{2,})(.*?)(?=\\s{2})(\\s{2})(\\w+)', // RegEx
                mapping: 'return builder.setFileName(matcher.group(1)).setMessage(matcher.group(7)).setLineStart(Integer.parseInt(matcher.group(3))).setCategory(matcher.group(5)).setType(matcher.group(9)).buildOptional()', // Mapping script
                example: """/home/jonasscharpf/git/check_mk/buildscripts/scripts/utils/upload_artifacts.groovy
                  39    error    The variable [versioning] in class None is not used  UnusedVariable
                  71    warning  Map [credentialsId:Release_Key, variable:RELEASE_KEY] is duplicated.  DuplicateMapLiteral""",  // example log message
            // |                                                    1                                                    |
            // |2|3|4| 5   |6|                                7                                 |8|          9           |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "JUNIT":
            issues.add(scanForIssues(
                tool: junitParser(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "MYPY":
            issues.add(scanForIssues(
                tool: myPy(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "PYLINT":
            issues.add(scanForIssues(
                tool: pyLint(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "SARIF":
            issues.add(scanForIssues(
                tool: sarif(
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "SHELLCHECK":
            parserId = "shellcheck";
            update_custom_parser([
                id: parserId, // ID
                name: 'Shellcheck', // Name shown on left side menu
                regex: '''(In)\\s(.*)\\s(.*)\\s(\\d*):\\n(.*)\\n(.*)(\\^-*\\^)\\s(\\w*\\d*)(?:\\:|\\s\\(\\w*\\)\\:)\\s(.*)''', // RegEx
                mapping: 'return builder.setFileName(matcher.group(2)).setCategory(matcher.group(8)).setMessage(matcher.group(9)).setLineStart(Integer.parseInt(matcher.group(4))).buildOptional()', // Mapping script
                example: """In ./enterprise/skel/etc/init.d/dcd line 14:
                . \"\$OMD_ROOT/.profile\"
                  ^------------------^ SC1091 (info): Not following: ./.profile: openBinaryFile: does not exist (No such file or directory)""",  // example log message
            // |1 |             2                 | 3  | 4 |
            // |         5        |
            // | 6 |      7       |  8   |  9   |  10                   |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "SHELLUNIT":
            parserId = "shellunit";
            update_custom_parser([
                id: parserId, // ID
                name: 'Shell Unittests', // Name shown on left side menu
                regex: '''(.*\\.sh)(.*)(ERROR)(.*\\(\\))(.*\\n)*(.*ASSERT.*)(.*\\n.*)*''', // RegEx
                mapping: 'return builder.setFileName(matcher.group(1)).setCategory(matcher.group(3)).setMessage(matcher.group(6)).buildOptional()', // Mapping script
                example: """tests/unit-shell/agents/test_set_up_path.shshunit2:ERROR test_set_up_path_already_in_path() returned non-zero return code.
                test_set_up_path_already_in_path
                ASSERT:expected:</foo:/usr/local/bin:/bar2> but was:</foo:/usr/local/bin:/bar>""",  // example log message
            // |                     1                             |  2   |  3  |             4                    |
            // |            5               |
            // |                          6                                               |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "TSJSBUILD":
            parserId = "tsjsbuild";
            update_custom_parser([
                id: parserId, // ID
                name: 'TS/JS build', // Name shown on left side menu
                regex: '(.*):\\s(.*):\\s(.*)\\s\\((\\d+):(\\d+)\\)', // RegEx
                mapping: 'return builder.setFileName(matcher.group(2)).setCategory(matcher.group(1)).setMessage(matcher.group(3)).setLineStart(Integer.parseInt(matcher.group(4))).setColumnStart(Integer.parseInt(matcher.group(5))).buildOptional()', // Mapping script
                example: "SyntaxError: web/htdocs/js/modules/dashboard.ts: Missing semicolon. (65:30)",  // example log message
            //       |     1     |                    2              |         3        | 4  |5 |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "TSJSTYPES":
            parserId = "tsjstypes";
            update_custom_parser([
                id: parserId, // ID
                name: 'TS/JS types', // Name shown on left side menu
                regex: '(.*\\..*(?:ts|js))\\((\\d+),(\\d+)\\):\\s(.*):\\s(.*)', // RegEx
                mapping: 'return builder.setFileName(matcher.group(1)).setCategory(matcher.group(4)).setMessage(matcher.group(5)).setLineStart(Integer.parseInt(matcher.group(2))).setColumnStart(Integer.parseInt(matcher.group(3))).buildOptional()', // Mapping script
                example: "web/htdocs/js/modules/dashboard.js(65,37): error TS1005: ',' expected.s",  // example log message
            //       |      1                           |2 | 3 |      4      |      5        |
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        case "RUFFFORMAT":
            parserId = "ruffformat";
            update_custom_parser([
                id: parserId, // ID
                name: 'Ruff Format', // Name shown on left side menu
                regex: '(^\\+\\+\\+\\s)(.*\\.py$)\\n(@@\\s\\-)(\\d)(\\,\\d\\s\\+.*\\s@@\\n)([\\s\\w\\+\\.\\-\\(\\@\\)]*\\n)*', // RegEx
                mapping: 'return builder.setFileName(matcher.group(2)).setLineStart(Integer.parseInt(matcher.group(4))).setMessage(matcher.group(6)).buildOptional()', // Mapping script
                example: """--- gui_e2e/test_menu_help.py
                +++ gui_e2e/test_menu_help.py
                @@ -7,8 +7,8 @@
                 import pytest

                 from tests.testlib.playwright.pom.dashboard import Dashboard
                +from tests.testlib.playwright.timeouts import handle_playwright_timeouterror
                """,  // example log message
            ]);
            issues.add(scanForIssues(
                tool: groovyScript(
                    parserId: parserId,
                    pattern: "${result_check_file_pattern}"
                )
            ));
            break;
        default:
            println("No tool defined for RESULT_CHECK_TYPE: ${result_check_type}");
            break;
    }

    if (! as_stage) {
        return issues;
    }
    publish_issue_stages(issues);
}
/* groovylint-enable MethodSize, LineLength */

// pusblish issues stage based on given issue parser(s)
void publish_issue_stages(issues) {
    if (issues) {
        stage("Publish issues") {
            publishIssues(
                issues: issues,
                trendChartType: "TOOLS_ONLY",
                qualityGates: [[
                    threshold: 1,
                    type: "TOTAL",
                    unstable: false,
                ]],
            );
        }
    }
    else {
        println("WARNING: No issue parsers given");
    }
}

// update custom parser with new configs, existing parsers will be overwritten
void update_custom_parser(Map config = [:]) {
    // update the default map content with the user provided config content
    // new key/value of provided map is automatically added to the defaultDict
    def defaultDict = [
        id: "",
        name: "",
        regex: "",
        mapping: "",
        example: "",
    ] << config;

    def parser_config = io.jenkins.plugins.analysis.warnings.groovy.ParserConfiguration.getInstance();
    def existing_parsers = parser_config.getParsers();

    def newParser = new io.jenkins.plugins.analysis.warnings.groovy.GroovyParser(
        defaultDict.id,
        defaultDict.name,
        defaultDict.regex,
        defaultDict.mapping,
        defaultDict.example
    );

    if (parser_config.contains(defaultDict.id)) {
        existing_parsers[existing_parsers.indexOf(newParser)] = newParser;
        parser_config.setParsers(existing_parsers);
    }
    else {
        parser_config.setParsers(existing_parsers.plus(newParser)); // groovylint-disable ExplicitCallToPlusMethod
    }
}

// Get registry credentials for a specific edition
String registry_credentials_id(edition) {
    switch (edition) {
        case "ultimate":
        case "ultimatemt":
        case "community":
        case "pro":
            return "11fb3d5f-e44e-4f33-a651-274227cc48ab";
        case "cloud":
            return "nexus";
        default:
            throw new Exception("Cannot provide registry credentials id for edition '${edition}'");     // groovylint-disable ThrowException
    }
}

void assert_fips_testing(use_case, node_labels) {
    if (use_case == "fips" && !node_labels.contains("fips")) {
        throw new Exception("FIPS testing requested but we're not running on a fips node.");
    }
}

return this;
