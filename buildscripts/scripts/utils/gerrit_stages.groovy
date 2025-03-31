#!groovy

/// file: gerrit_stages.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def desc_init() {
    // add new content to next line, but do not overwrite existing content
    currentBuild.description += "<br>";
}

def desc_add_line(TEXT) {
    currentBuild.description += "<p>${TEXT}</p>";
}

def desc_add_table_bottom() {
    currentBuild.description += "</table>";
}

def desc_add_table(items_list) {
    currentBuild.description += """<table><tr><th>${items_list.join("</th><th>")}</th></tr>""";
}

def desc_add_status_row_gerrit(Map args) {
    // 'Stage'                    'Duration'      'Status'  'Parsed results'                'Result files'
    // Python Typing(<-JOB_URL)   11.078 seconds  success   (Analyser URL (<-ANALYSER_URL))  results/python-typing.txt(<-ARTIFACTS_URL)
    def pattern_url = "n/a";
    def triggered_build = args.stepName;
    def parser_warnings = "n/a";

    if (args.pattern != null && args.pattern != '--') {
        pattern_url = """<a href="artifact/${args.pattern}">${args.pattern}</a>""";
    }

    if (args.triggered_build_url) {
        triggered_build = """<a href="${args.triggered_build_url}">${args.stepName}</a>""";
    }

    if (args.unique_parser_name) {
        parser_warnings = """<a href="${currentBuild.absoluteUrl}/${args.unique_parser_name}">Warnings""";
    }

    def additional_desc = """<tr>
    <td>${triggered_build}</td>
    <td>${args.duration}</td>
    <td style=\"color: ${['success': 'green', 'skipped': 'grey', 'failure': 'red'][args.status]};\">${args.status}</td>
    <td>${parser_warnings}</td>
    <td>${pattern_url}</td>
    </tr>""";
    currentBuild.description += additional_desc;
}

return this;
