/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "select2";

import {select} from "d3";
import $ from "jquery";
import type {QueryOptions} from "select2";

import {call_ajax} from "./ajax";
//TODO: this causes an error because allowJS is set to false in tsconfig
// colorpicker should be used as a package instead of copied file
//@ts-ignore
import {ColorPicker} from "./colorpicker";
import {
    enable_dynamic_form_elements,
    enable_select2_dropdowns,
    format_select2_item,
} from "./forms";
import {close_popup} from "./popup_menu";
import type {Nullable} from "./utils";
import {
    add_class,
    add_simplebar_scrollbar,
    execute_javascript_by_object,
    has_class,
    prevent_default_events,
    querySelectorID,
    remove_class,
} from "./utils";

//#   +--------------------------------------------------------------------+
//#   | Functions needed by HTML code from ValueSpec (valuespec.py)        |
//#   '--------------------------------------------------------------------'

const dynamicParamsCallbacks = {
    nop(autocompleter: AutoCompleter, _elem: HTMLSelectElement) {
        return {
            ...autocompleter.params,
        };
    },
    tag_group_options_autocompleter(
        autocompleter: GroupAutocompleterConfig,
        elem: HTMLSelectElement,
    ) {
        return {
            group_id: (
                document.getElementById(
                    elem.id.replace(/_val$/, "_grp"),
                ) as HTMLInputElement
            ).value,
            ...autocompleter.params,
        };
    },
    host_and_service_hinted_autocompleter(
        autocompleter: ContextAutocompleterConfig,
        elem: HTMLSelectElement,
    ) {
        // fetch metrics, filtered by hostname and service from another input field
        // DropdownChoiceWithHostAndServiceHints
        const obj: Record<string, Record<string, Record<string, string>>> = {};
        let hint = (
            document.getElementById(
                `${elem.id}_hostname_hint`,
            ) as HTMLInputElement
        ).value;
        if (hint) {
            obj["context"] ??= {};
            obj["context"]["host"] = {};
            obj["context"]["host"]["host"] = hint;
        }
        hint = (
            document.getElementById(
                `${elem.id}_service_hint`,
            ) as HTMLInputElement
        ).value;
        if (hint) {
            obj["context"] ??= {};
            obj["context"]["service"] = {};
            obj["context"]["service"]["service"] = hint;
        }

        return {
            ...obj,
            ...autocompleter.params,
        };
    },
    host_hinted_autocompleter(
        autocompleter: ContextAutocompleterConfig,
        elem: HTMLSelectElement,
    ) {
        // fetch services, filtered by host name of another input field
        const host_id = elem.id.endsWith("_service_hint")
            ? `${elem.id.slice(0, -13)}_hostname_hint`
            : "context_host_p_host";
        const val_or_empty = (obj: HTMLSelectElement | null) =>
            obj ? {host: {host: obj.value}} : {};

        return {
            context: val_or_empty(
                <HTMLSelectElement | null>document.getElementById(host_id),
            ),
            ...autocompleter.params,
        };
    },
    label_autocompleter(autocompleter: AutoCompleter, elem: HTMLSelectElement) {
        const label_selects_of_group = elem
            .closest(".label_group")!
            .getElementsByClassName(
                "label",
            ) as HTMLCollectionOf<HTMLOptionElement>;
        const group_labels: string[] = [];

        for (const label of label_selects_of_group) {
            if (label.value) {
                group_labels.push(label.value);
            }
        }
        return {
            world: elem.dataset.world,
            context: {group_labels: group_labels},
            ...autocompleter.params,
        };
    },
};

//I got these types from cmk/gui/utils/autocompleter_config.py
type DynamicParamsCallbackName = keyof typeof dynamicParamsCallbacks;

type AutoCompleterGroupType =
    | "host"
    | "service"
    | "contact"
    //kubernetes:
    | "cluster"
    | "node"
    | "deployment"
    | "namespace"
    | "daemonset"
    | "statefulset";

interface AutoCompleterParams {
    strict: boolean;
}

interface ContextAutocompleterConfigParams extends AutoCompleterParams {
    show_independent_of_context: boolean;
}

interface GroupAutocompleterConfigParams extends AutoCompleterParams {
    group_type: AutoCompleterGroupType;
}

type AutoCompleterConfigIdent =
    | "monitored_hostname"
    | "monitored_service_description"
    | "check_cmd"
    | "sites"
    | "tag_groups"
    | "tag_group_opt"
    | "kubernetes_labes"
    | "service_levels"
    | "syslog_facilities"
    | "graph_template_for_combined_graph";

type ContextAutocompleterConfigIdent =
    | "monitored_service_description"
    | "available_graph_templates"
    | "monitored_metrics";

type GroupAutocompleterConfigIdent = "allgroups" | "kubernetes_labels";

interface AbstractAutoCompleter {
    ident: string;
    dynamic_params_callback_name?: DynamicParamsCallbackName;
    params: AutoCompleterParams;
}

interface AutoCompleterConfig extends AbstractAutoCompleter {
    ident: AutoCompleterConfigIdent;
    dynamic_params_callback_name?: DynamicParamsCallbackName;
    params: AutoCompleterParams;
}

interface ContextAutocompleterConfig extends AbstractAutoCompleter {
    ident: ContextAutocompleterConfigIdent;
    dynamic_params_callback_name?: DynamicParamsCallbackName;
    params: ContextAutocompleterConfigParams;
}

interface GroupAutocompleterConfig extends AbstractAutoCompleter {
    ident: GroupAutocompleterConfigIdent;
    dynamic_params_callback_name?: DynamicParamsCallbackName;
    params: GroupAutocompleterConfigParams;
}

type AutoCompleter =
    | AutoCompleterConfig
    | ContextAutocompleterConfig
    | GroupAutocompleterConfig;

type Choice = [string, string];
type Choices = Choice[];

interface AutoCompleteAjaxResponse {
    result_code: 0 | 1 | 2;
    result: {choices: Choices};
    severity: "success" | "error";
}

interface TableEntries {
    sort_value: string;
    row_node: HTMLTableRowElement;
}

export function toggle_option(
    oCheckbox: HTMLInputElement,
    divid: string,
    negate: 1 | 0,
) {
    const oDiv = document.getElementById(divid)!;
    if ((oCheckbox.checked && !negate) || (!oCheckbox.checked && negate))
        oDiv.style.display = "";
    else oDiv.style.display = "none";
}

export function toggle_dropdown(oDropdown: HTMLInputElement, divid: string) {
    const oDiv = document.getElementById(divid)!;
    if (oDropdown.value == "other") oDiv.style.display = "";
    else oDiv.style.display = "none";
}

export function toggle_tag_dropdown(
    oDropdown: HTMLInputElement,
    divid: string,
) {
    const oDiv = document.getElementById(divid)!;
    if (oDropdown.value == "ignore") oDiv.style.display = "none";
    else oDiv.style.display = "";
}

/* This function is called after the table with of input elements
   has been rendered. It attaches the onFocus-function to the last
   of the input elements. That function will append another
   input field as soon as the user focusses the last field. */
export function list_of_strings_init(
    divid: string,
    split_on_paste: boolean,
    split_separators: string,
) {
    const container = document.getElementById(divid)!;
    const children = container.getElementsByTagName("div");
    let last_input: HTMLInputElement | HTMLSelectElement =
        children[children.length - 1].getElementsByTagName("input")[0];
    if (!last_input)
        last_input =
            children[children.length - 1].getElementsByTagName("select")[0];
    list_of_strings_add_event_handlers(
        last_input,
        split_on_paste,
        split_separators,
    );
}

function list_of_strings_add_event_handlers(
    input: HTMLElement,
    split_on_paste: boolean,
    split_separators: string,
) {
    const handler_func = function () {
        if (this.value != "") {
            return list_of_strings_extend(
                this,
                split_on_paste,
                split_separators,
            );
        }
    };
    const new_entries_from_event = (e: Event) => {
        // Get pasted data via clipboard API
        const clipboard_data =
            (e as ClipboardEvent).clipboardData ||
            (window as any).clipboardData;
        const pasted = clipboard_data!.getData("Text");

        // When pasting a string, trim separators and then split by the given separators
        const stripped = pasted.replace(
            new RegExp(
                "^[" + split_separators + "]+|[" + split_separators + "]+$",
                "g",
            ),
            "",
        );
        return stripped.split(new RegExp("[" + split_separators + "]+"));
    };

    const setup_new_entries = (
        anchor: HTMLInputElement | HTMLSelectElement,
        event: Event,
    ) => {
        const entries = new_entries_from_event(event);
        let last_input = anchor;
        // Add splitted parts to the input fields
        entries.forEach((entry: string, i: number) => {
            // Put the first item to the current field
            if (i != 0) last_input = list_of_strings_add_new_field(last_input);

            if (last_input.tagName == "INPUT") last_input.value = entry;
            else set_select2_element(last_input as HTMLSelectElement, entry);
        });

        // Focus the last populated field
        last_input.focus();
        // And finally add a new empty field to the end (with attached handlers)
        list_of_strings_extend(last_input, split_on_paste, split_separators);

        // Stop original data actually being pasted
        return prevent_default_events(event);
    };

    if (input.tagName == "INPUT") {
        input.onfocus = handler_func;
        input.oninput = handler_func;

        if (split_on_paste) {
            input.onpaste = function (event) {
                if ((<HTMLInputElement>this).value != "") return true; // The field had a value before: Don't do custom stuff
                return setup_new_entries(<HTMLInputElement>this, event);
            };
        }
    } else {
        $(input).on("select2:select", handler_func);

        if (split_on_paste) {
            $(input).on("select2:open", () => {
                const search_field = $(".select2-search input");
                search_field.on("paste", event => {
                    if (search_field.val() != "") return true; // The field had a value before: Don't do custom stuff
                    return setup_new_entries(
                        <HTMLSelectElement>input,
                        event.originalEvent!,
                    );
                });
            });
        }
    }
}

function list_of_strings_remove_event_handlers(input: HTMLElement) {
    if (input.tagName == "INPUT") {
        input.oninput = null;
        input.onfocus = null;
        input.onpaste = null;
    } else {
        $(input).off("select2:select");
        $(input).off("select2:open");
    }
}

/* Is called when the last input field in a ListOfString gets focus.
   In that case a new input field is being appended. */
export function list_of_strings_extend(
    input: HTMLInputElement | HTMLSelectElement,
    split_on_paste: boolean,
    split_separators: string,
) {
    const new_input = list_of_strings_add_new_field(input);

    /* Move focus function from old last to new last input field */
    list_of_strings_add_event_handlers(
        new_input,
        split_on_paste,
        split_separators,
    );
    list_of_strings_remove_event_handlers(input);
}

function list_of_strings_add_new_field(
    input: HTMLInputElement | HTMLSelectElement,
) {
    /* The input field has a unique name like "extra_emails_2" for the field with
       the index 2. We need to convert this into "extra_emails_3". */

    const old_name = input.name;
    const splitted = old_name.split("_");
    const num = 1 + parseInt(splitted[splitted.length - 1]);
    splitted[splitted.length - 1] = "" + num;
    const new_name = splitted.join("_");

    /* Now create a new <div> element as a copy from the current one and
       replace this name. We do this by simply copying the HTML code. The
       last field is always empty. Remember: ListOfStrings() always renders
       one exceeding empty element. */

    let div = input.parentNode as HTMLElement;
    while (
        (div.parentNode as HTMLElement).classList &&
        !(div.parentNode as HTMLElement).classList.contains("listofstrings")
    )
        div = div.parentNode as HTMLElement;
    const container = div.parentNode!;

    const tagtype = input.tagName == "INPUT" ? "input" : "select";
    const new_div = document.createElement("DIV");
    if (input.tagName == "INPUT") {
        /* eslint-disable no-unsanitized/property -- Highlight existing violations CMK-17846 */
        new_div.innerHTML = div.innerHTML.replace(
            '"' + old_name + '"',
            '"' + new_name + '"',
        );
        // Do not clone placeholder help texts
        select(new_div).select("input").attr("placeholder", null);
        // IE7 does not have quotes in innerHTML, trying to workaround this here.
        new_div.innerHTML = new_div.innerHTML.replace(
            "=" + old_name + " ",
            "=" + new_name + " ",
        );
        new_div.innerHTML = new_div.innerHTML.replace(
            "=" + old_name + ">",
            "=" + new_name + ">",
        );
        /* eslint-enable no-unsanitized/property -- Highlight existing violations CMK-17846 */
    } else {
        // shallow because select2 ands dynamically some spans with form_elements
        const new_select = input.cloneNode() as HTMLInputElement;
        new_select.name = new_name;
        new_select.id = new_name;
        delete new_select.dataset.select2Id;
        new_div.appendChild(new_select);
    }
    enable_dynamic_form_elements(new_div);
    container.appendChild(new_div);

    return new_div.getElementsByTagName(tagtype)[0] as
        | HTMLInputElement
        | HTMLSelectElement;
}

const cascading_sub_valuespec_parameters = {} as any;

interface CascadingSubValuespecParameters {
    page_name: string | null;
    request_vars: {
        varprefix: string;
        choice_id: null | string | boolean | number;
        encoded_value: any;
    };
}

export function add_cascading_sub_valuespec_parameters(
    varprefix: string,
    parameters: CascadingSubValuespecParameters,
) {
    cascading_sub_valuespec_parameters[varprefix] = parameters;
}

export function cascading_change(
    oSelect: HTMLInputElement,
    varprefix: string,
    count: number,
) {
    const nr = parseInt(oSelect.value);

    for (let i = 0; i < count; i++) {
        const vp = varprefix + "_" + i;
        const container = document.getElementById(vp + "_sub");
        if (!container) continue;

        container.style.display = nr == i ? "" : "none";

        // In case the rendering has been postponed for this cascading
        // valuespec ask the configured AJAX page for rendering the sub
        // valuespec input elements
        if (
            nr == i &&
            container.childElementCount == 0 &&
            Object.prototype.hasOwnProperty.call(
                cascading_sub_valuespec_parameters,
                vp,
            )
        ) {
            show_cascading_sub_valuespec(
                vp,
                cascading_sub_valuespec_parameters[vp],
            );
        }
    }
}

function show_cascading_sub_valuespec(
    varprefix: string,
    parameters: CascadingSubValuespecParameters,
) {
    const post_data =
        "request=" +
        encodeURIComponent(JSON.stringify(parameters["request_vars"]));

    call_ajax(parameters["page_name"] + ".py", {
        method: "POST",
        post_data: post_data,
        response_handler: function (
            handler_data: {varprefix: string},
            ajax_response: string,
        ) {
            const response = JSON.parse(ajax_response);
            if (response.result_code != 0) {
                console.log(
                    "Error [" + response.result_code + "]: " + response.result,
                ); // eslint-disable-line
                return;
            }

            const container = document.getElementById(
                handler_data.varprefix + "_sub",
            )!;
            /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
            container.innerHTML = response.result.html_code;

            execute_javascript_by_object(container);
            enable_dynamic_form_elements(container);
        },
        handler_data: {
            varprefix: varprefix,
        },
    });
}

export function textarea_resize(oArea: HTMLInputElement) {
    oArea.style.height = oArea.scrollHeight - 6 + "px";
}

export function listof_add(
    varprefix: string,
    magic: string,
    style: string | null,
) {
    const count_field = document.getElementById(
        varprefix + "_count",
    ) as HTMLInputElement;
    const count = parseInt(count_field.value);
    let str_count = "" + (count + 1);

    // Make sure the new entry we're creating does not already exist. We cannot rely on the count
    // value here -> increment the count until the according id does not exist
    while (document.querySelector(`[id^=${varprefix}][id$="${str_count}"]`)) {
        str_count = "" + (parseInt(str_count) + 1);
    }
    count_field.value = str_count;

    const html_code = listof_get_new_entry_html_code(
        varprefix,
        magic,
        str_count,
    );
    const container = document.getElementById(varprefix + "_container");

    let new_child: HTMLElement;
    const tmp_container = document.createElement("div");
    if (style == "floating") {
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        tmp_container.innerHTML = html_code;
        new_child = tmp_container.children[0] as HTMLElement;
    } else {
        // Hack for IE. innerHTML does not work correctly directly on tbody/tr
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        tmp_container.innerHTML =
            "<table><tbody>" + html_code + "</tbody></tr>";
        new_child = tmp_container.children[0].children[0]
            .children[0] as HTMLElement; // TR
    }

    container!.appendChild(new_child);
    execute_javascript_by_object(new_child);
    enable_dynamic_form_elements(new_child);

    listof_update_indices(varprefix);
}

function listof_get_new_entry_html_code(
    varprefix: string,
    magic: string,
    str_count: string,
) {
    const container = document.getElementById(varprefix + "_container")!;
    let oPrototype: HTMLElement | null = null;
    if (container.children.length == 0) {
        // Adding the first element. See if there's a specific prototype given for the first
        // element, i.e. the first element is rendered differently than the subsequent ones.
        oPrototype = document.getElementById(
            varprefix + "_first_elem_prototype",
        );
    }
    if (oPrototype == null) {
        oPrototype = document.getElementById(varprefix + "_prototype")!;
    }

    const encoded_magic = encodeURIComponent(magic).replace("!", "%21");

    let html_code = oPrototype.innerHTML;

    // Remove the "_first_elem" string that's appended to the prototype's indices, in case there is
    // a specific first element rendering. We do not need it for the visible entries and this makes
    // retrieving the data from HTTP vars easier.
    html_code = html_code.replace(
        new RegExp(magic + "_first_elem", "g"),
        magic,
    );
    // Replace the magic in simple strings
    ["_entry_", "_indexof_", "_orig_indexof_", "_"].forEach(element => {
        [magic, encoded_magic].forEach(magic => {
            const old_name = varprefix + element + magic;
            const new_name = varprefix + element + str_count;
            html_code = html_code.replace(new RegExp(old_name, "g"), new_name);
        });
    });

    // Complex magic replacements within functions
    // Note: the listof_drop_handler will also work with a broken magic.. but we should convert it anyway
    const complex_replacements: [string, string][] = [
        [
            "listof_drop_handler\\({&quot;cur_index&quot;: &quot;" +
                magic +
                "&quot;, &quot;varprefix&quot;: &quot;" +
                varprefix +
                "&quot;}",
            "listof_drop_handler({&quot;cur_index&quot;: &quot;" +
                str_count +
                "&quot;, &quot;varprefix&quot;: &quot;" +
                varprefix +
                "&quot;}",
        ],
        [
            "listof_drop_handler\\({&quot;cur_index&quot;: &quot;" +
                encoded_magic +
                "&quot;, &quot;varprefix&quot;: &quot;" +
                varprefix +
                "&quot;}",
            "listof_drop_handler({&quot;cur_index&quot;: &quot;" +
                str_count +
                "&quot;, &quot;varprefix&quot;: &quot;" +
                varprefix +
                "&quot;}",
        ],
        [
            "listof_delete\\(&quot;" +
                varprefix +
                "&quot;, &quot;" +
                magic +
                "&quot;\\)",
            "listof_delete(&quot;" +
                varprefix +
                "&quot;, &quot;" +
                str_count +
                "&quot;)",
        ],
        [
            "listof_delete\\(&quot;" +
                varprefix +
                "&quot;, &quot;" +
                encoded_magic +
                "&quot;\\)",
            "listof_delete(&quot;" +
                varprefix +
                "&quot;, &quot;" +
                str_count +
                "&quot;)",
        ],
        [
            "label_group_delete\\(&quot;" +
                varprefix +
                "&quot;, &quot;" +
                magic +
                "&quot;",
            // we do not escape the bracket here as we cannot know all the function arguments and
            // thus cannot close the brackets. escaping only the opening bracket would make the
            // function call fail.
            "label_group_delete(&quot;" +
                varprefix +
                "&quot;, &quot;" +
                str_count +
                "&quot;",
        ],
    ];
    complex_replacements.forEach(element => {
        const [key, replacement] = element;
        html_code = html_code.replace(new RegExp(key, "g"), replacement);
    });

    return html_code;
}

export function listof_delete(varprefix: string, nr: string) {
    const entry = document.getElementById(varprefix + "_entry_" + nr)!;
    entry.parentNode!.removeChild(entry);
    listof_update_indices(varprefix);
}

export function listof_drop_handler(handler_args: {
    cur_index: string;
    varprefix: string;
}) {
    const varprefix = handler_args.varprefix;
    const cur_index = handler_args.cur_index;

    const indexof: NodeListOf<HTMLElement> = document.getElementsByName(
        varprefix + "_indexof_" + cur_index,
    );
    if (indexof.length == 0) throw "Failed to find the indexof_fied";
    const firstIndexof = indexof[0];

    // Find the tbody parent of the given tag type
    let tbody: ParentNode | null = firstIndexof;
    while (tbody && (tbody as HTMLElement).tagName != "TBODY")
        tbody = tbody.parentNode;

    if (!tbody) throw "Failed to find the tbody element of " + firstIndexof;

    listof_update_indices(varprefix);
}

export function listof_sort(
    varprefix: string,
    _magic: string,
    sort_by: number | null,
) {
    const tbody = document.getElementById(
        varprefix + "_container",
    ) as HTMLTableElement;
    const rows = tbody.rows;

    const entries: TableEntries[] = [];
    let i;
    let td;
    let sort_field_name;
    for (i = 0; i < rows.length; i++) {
        // Find the index of this row
        td = rows[i].cells[0]; /* TD with buttons */
        if (td.children.length == 0) continue;
        const index = (
            td.getElementsByClassName("orig_index")[0] as HTMLInputElement
        ).value;

        sort_field_name = varprefix + "_" + index + "_" + sort_by;

        // extract the sort field value and add it to the entries list
        // together with the row to be moved
        const fields = document.getElementsByName(sort_field_name);
        if (fields.length == 0) {
            return; // abort sorting
        }

        entries.push({
            sort_value: (fields[0] as HTMLInputElement).value,
            row_node: rows[i],
        });
    }

    entries.sort(function (a, b) {
        if (a.sort_value.toLowerCase() < b.sort_value.toLowerCase()) {
            return -1;
        }
        if (a.sort_value.toLowerCase() > b.sort_value.toLowerCase()) {
            return 1;
        }
        return 0;
    });

    // Remove all rows from the list and then add the rows back to it
    // in sorted order

    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }

    for (i = 0; i < entries.length; i++) {
        tbody.appendChild(entries[i].row_node);
    }

    listof_update_indices(varprefix);
}

export function listof_update_indices(varprefix: string) {
    const container = document.getElementById(varprefix + "_container")!;

    for (let i = 0; i < container.children.length; i++) {
        const child_node = container.children[i];
        const index = child_node.getElementsByClassName(
            "index",
        )[0] as HTMLInputElement;
        if (index.value === "") {
            // initialization of recently added row
            const orig_index = child_node.getElementsByClassName(
                "orig_index",
            )[0] as HTMLInputElement;
            orig_index.value = "" + (i + 1);
        }
        index.value = "" + (i + 1);
    }
}

export function list_choice_toggle_all(varprefix: string) {
    const tbl = document.getElementById(varprefix + "_tbl")!;
    const checkboxes = tbl.getElementsByTagName("input");
    if (!checkboxes) return;

    // simply use state of first texbox as base
    const state = !checkboxes[0].checked;
    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = state;
    }
}

export function rule_comment_prefix_date_and_user(
    img: HTMLAnchorElement,
    text: string,
) {
    const container = <HTMLElement>img.parentNode!.parentNode;
    const textarea = container.getElementsByTagName("textarea")[0];

    if (!textarea) {
        //console.log("Failed to find textarea object");
        return;
    }

    textarea.value = text + "\n" + textarea.value;
    textarea.focus();
    textarea.setSelectionRange(text.length, text.length);
}

export function passwordspec_randomize(img: HTMLAnchorElement, pwlen: number) {
    let a,
        c,
        password = "";
    while (password.length < pwlen) {
        a = Math.trunc(Math.random() * 128);
        if (
            (a >= 97 && a <= 122) ||
            (a >= 65 && a <= 90) ||
            (a >= 48 && a <= 57)
        ) {
            c = String.fromCharCode(a);
            password += c;
        }
    }
    let oInput = img.previousElementSibling;
    if ((oInput as HTMLElement).tagName != "INPUT")
        oInput = oInput!.children[0]; // in complain mode
    (oInput as HTMLInputElement).value = password;
}

export function toggle_hidden(img: HTMLAnchorElement) {
    let oInput: Element = img;
    while (!(oInput instanceof HTMLInputElement))
        oInput = oInput.previousElementSibling!;
    if (oInput.type == "text") {
        oInput.type = "password";
    } else {
        oInput.type = "text";
    }
}

export function duallist_enlarge(field_suffix: string, varprefix: string) {
    const field = document.getElementById(varprefix + "_" + field_suffix)!;
    let other_id;
    if (field.id != varprefix + "_selected") {
        // The other field is the one without "_unselected" suffix
        other_id = varprefix + "_selected";
    } else {
        // The other field is the one with "_unselected" suffix
        other_id = varprefix + "_unselected";
    }

    const other_field = document.getElementById(other_id);
    if (!other_field) return;

    remove_class(other_field, "large");
    add_class(other_field, "small");
    remove_class(field, "small");
    add_class(field, "large");
}

export function duallist_switch(
    field_suffix: string,
    varprefix: string,
    keeporder: number,
) {
    const field = document.getElementById(
        varprefix + "_" + field_suffix,
    ) as HTMLSelectElement;
    let other_id, positive;
    if (field.id != varprefix + "_selected") {
        // The other field is the one without "_unselected" suffix
        other_id = varprefix + "_selected";
        positive = true;
    } else {
        // The other field is the one with "_unselected" suffix
        other_id = varprefix + "_unselected";
        positive = false;
    }

    const other_field = document.getElementById(other_id) as HTMLSelectElement;
    if (!other_field) return;

    const helper = document.getElementById(varprefix) as HTMLInputElement;
    if (!helper) return;

    // Move the selected options to the other select field
    const selected: HTMLOptionElement[] = [];
    let i;
    for (i = 0; i < field.options.length; i++) {
        if (field.options[i].selected) {
            selected.push(field.options[i]);
        }
    }
    if (selected.length == 0) return; // when add/remove clicked, but none selected

    // Now loop over all selected elements and add them to the other field
    for (i = 0; i < selected.length; i++) {
        // remove option from origin
        field.removeChild(selected[i]);
        other_field.appendChild(selected[i]);

        selected[i].selected = false;
    }

    // Determine the correct child to insert. If keeporder is being set,
    // then new elements will aways be appended. That way the user can
    // create an order of his choice. This is being used if DualListChoice
    // has the option custom_order = True
    if (!keeporder) {
        sort_select(other_field);
    }

    // Update internal helper field which contains a list of all selected keys
    const pos_field = positive ? other_field : field;

    const texts: string[] = [];
    for (i = 0; i < pos_field.options.length; i++) {
        texts.push(pos_field.options[i].value);
    }
    helper.value = texts.join("|");
}

function sort_select(select: HTMLSelectElement) {
    let choices: [string, string, boolean][] = [];
    let i;
    for (i = 0; i < select.options.length; i++) {
        choices[i] = [
            select.options[i].text,
            select.options[i].value,
            select.options[i].disabled,
        ];
    }

    const collator = new Intl.Collator(undefined, {
        numeric: true,
        sensitivity: "base",
    });
    choices = choices.sort(
        (a, b) =>
            collator.compare(a[0], b[0]) ||
            collator.compare(String(a[1]), String(b[1])) ||
            collator.compare(String(a[2]), String(b[2])),
    );
    while (select.options.length > 0) {
        // @ts-ignore
        select.options[0] = null;
    }

    for (i = 0; i < choices.length; i++) {
        const op = new Option(choices[i][0], choices[i][1]);
        op.disabled = choices[i][2];
        select.options[i] = op;
    }

    return;
}

export function iconselector_select(
    _event: Event,
    varprefix: string,
    value: string,
) {
    // set value of valuespec
    const obj = document.getElementById(
        varprefix + "_value",
        //not sure if this cast is correct
    ) as HTMLInputElement;
    obj.value = value;

    const src_img = document.getElementById(
        varprefix + "_i_" + value,
    ) as HTMLImageElement;

    // Set the new choosen icon in the valuespecs image
    const img = document.getElementById(varprefix + "_img") as HTMLImageElement;
    img.src = src_img.src;

    close_popup();
}

export function iconselector_toggle(varprefix: string, category_name: string) {
    // Update the navigation
    const nav_links = document.getElementsByClassName(varprefix + "_nav");
    let i;
    for (i = 0; i < nav_links.length; i++) {
        if (nav_links[i].id == varprefix + "_" + category_name + "_nav")
            add_class(
                nav_links[i].parentNode as Nullable<HTMLElement>,
                "active",
            );
        else
            remove_class(
                nav_links[i].parentNode as Nullable<HTMLElement>,
                "active",
            );
    }

    // Now update the category containers
    const containers = document.getElementsByClassName(
        varprefix + "_container",
    ) as HTMLCollectionOf<HTMLElement>;
    for (i = 0; i < containers.length; i++) {
        if (containers[i].id == varprefix + "_" + category_name + "_container")
            containers[i].style.display = "";
        else containers[i].style.display = "none";
    }
}

export function iconselector_toggle_names(_event: Event, varprefix: string) {
    const icons = document.getElementById(varprefix + "_icons");
    if (has_class(icons, "show_names")) remove_class(icons, "show_names");
    else add_class(icons, "show_names");
}

export function listofmultiple_add(
    varprefix: string,
    choice_page_name: string,
    page_request_vars: Record<string, any>,
    trigger?: HTMLAnchorElement,
) {
    let ident;
    let triggerElement: HTMLAnchorElement | HTMLOptionElement | undefined =
        trigger;
    if (trigger) {
        // trigger given: Special case for ViewFilterList style choice rendering
        ident = trigger.id.replace(varprefix + "_add_", "");
        add_class(trigger, "disabled");
    } else {
        const choice = document.getElementById(
            varprefix + "_choice",
        ) as HTMLSelectElement;
        ident = choice.value;

        if (ident == "") return;

        triggerElement = choice.options[choice.selectedIndex];

        // disable this choice in the "add choice" select field
        triggerElement.disabled = true;
    }

    const request: Record<string, any> = {
        varprefix: varprefix,
        ident: ident,
    };

    // Add given valuespec specific request vars
    for (const prop in page_request_vars) {
        if (Object.prototype.hasOwnProperty.call(page_request_vars, prop)) {
            request[prop] = page_request_vars[prop];
        }
    }

    const post_data = "request=" + encodeURIComponent(JSON.stringify(request));

    call_ajax(choice_page_name + ".py", {
        method: "POST",
        post_data: post_data,
        handler_data: {
            trigger: triggerElement,
            ident: ident,
        },
        response_handler: function (handler_data, ajax_response: string) {
            const table = document.getElementById(
                varprefix + "_table",
            ) as HTMLTableElement;
            const tbody = table.getElementsByTagName("tbody")[0];

            const response = JSON.parse(ajax_response);
            if (response.result_code != 0) {
                console.log(
                    "Error [" + response.result_code + "]: " + response.result,
                ); // eslint-disable-line
                return;
            }

            const ident = handler_data.ident;
            // Update select2 to make the disabled attribute be recognized by the dropdown
            // (See https://github.com/select2/select2/issues/3347)
            const choice = document.getElementById(varprefix + "_choice");
            if (choice) {
                const choice_select2 = $(choice).select2();
                // Unselect the chosen option
                choice_select2.val("").trigger("change");
            }

            const tmp_container = document.createElement("tbody");
            /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
            tmp_container.innerHTML = response.result.html_code;
            const new_row = tmp_container.childNodes[0] as HTMLElement;
            if (new_row.tagName != "TR") {
                console.log(
                    "Error: Invalid choice HTML code: " +
                        response.result.html_code,
                ); // eslint-disable-line
                return;
            }

            tbody.insertBefore(new_row, tbody.firstChild);
            enable_dynamic_form_elements(new_row);
            execute_javascript_by_object(new_row);

            // Add it to the list of active elements
            const active = document.getElementById(
                varprefix + "_active",
            ) as HTMLInputElement;
            if (active.value != "") active.value += ";" + ident;
            else active.value = ident;

            // Put in a line break following the table if the added row is the first
            if (tbody.childNodes.length == 1)
                table.parentNode!.insertBefore(
                    document.createElement("br"),
                    table.nextSibling,
                );

            // Enable the reset button
            const reset_button = document.getElementById(
                varprefix + "_reset",
            ) as HTMLButtonElement;
            if (reset_button) reset_button.disabled = false;
        },
    });
}

export function listofmultiple_del(varprefix: string, ident: string) {
    // make the filter invisible
    const row = document.getElementById(varprefix + "_" + ident + "_row")!;
    const tbody = row.parentNode;
    tbody!.removeChild(row);

    // Make it choosable from the dropdown field again
    let choice = document.getElementById(
        varprefix + "_choice",
    ) as HTMLSelectElement | null;
    let i;
    if (choice) {
        for (i = 0; i < choice.options.length; i++)
            if (choice.options[i].value == ident)
                choice.options[i].disabled = false;

        // Update select2 to make the disabled attribute be recognized by the dropdown
        // (See https://github.com/select2/select2/issues/3347)
        $(choice).select2();
    } else {
        // trigger given: Special case for ViewFilterList style choice rendering
        choice = document.getElementById(
            varprefix + "_add_" + ident,
        ) as HTMLSelectElement;
        remove_class(choice, "disabled");
    }

    // Remove it from the list of active elements
    const active = document.getElementById(
        varprefix + "_active",
    ) as HTMLInputElement;
    const l = active.value.split(";");
    for (i = 0; i < l.length; i++) {
        if (l[i] == ident) {
            l.splice(i, 1);
            break;
        }
    }
    active.value = l.join(";");

    // Remove the line break following the table if the deleted row was the last
    if (tbody!.childNodes.length === 0) {
        const table = document.getElementById(varprefix + "_table")!;
        const br = table.nextSibling!;
        if (br.nodeName == "BR") br.parentNode!.removeChild(br);
    }

    // Enable the reset button
    const reset_button = document.getElementById(
        varprefix + "_reset",
    ) as HTMLButtonElement;
    if (reset_button) reset_button.disabled = false;
}

export function listofmultiple_init(varprefix: string, was_submitted: boolean) {
    const table = document.getElementById(varprefix + "_table")!;
    const tbody = table.getElementsByTagName("tbody")[0];

    const choice_field = document.getElementById(
        varprefix + "_choice",
    ) as null | HTMLOptionElement;
    if (choice_field) choice_field.value = "";

    listofmultiple_disable_selected_options(varprefix);
    // Put in a line break following the table if it's not empty
    if (tbody.childNodes.length >= 1)
        table.parentNode!.insertBefore(
            document.createElement("br"),
            table.nextSibling,
        );

    // Disable the reset button if the form was not submitted yet
    const reset_button = document.getElementById(
        varprefix + "_reset",
    ) as null | HTMLButtonElement;
    if (reset_button && !was_submitted) {
        reset_button.disabled = true;
    }
}

// The <option> elements in the <select> field of the currently chosen
// elements need to be disabled.
function listofmultiple_disable_selected_options(varprefix: string) {
    const active = document.getElementById(
        varprefix + "_active",
    ) as HTMLOptionElement;
    if (active.value == "") {
        return;
    }

    const active_choices = active.value.split(";");
    const choice_field = document.getElementById(
        varprefix + "_choice",
    ) as null | HTMLSelectElement;
    let i;
    if (choice_field) {
        for (i = 0; i < choice_field.options.length; i++) {
            if (active_choices.indexOf(choice_field.options[i].value) !== -1) {
                choice_field.options[i].disabled = true;
            }
        }
    } else {
        // trigger given: Special case for ViewFilterList style choice rendering
        let choice;
        for (i = 0; i < active_choices.length; i++) {
            choice = document.getElementById(
                varprefix + "_add_" + active_choices[i],
            );
            add_class(choice, "disabled");
        }
    }
}

function set_select2_element(elem: HTMLSelectElement, value: string) {
    if (!value || value == "null") return;
    const newval = new Option(value, value, false, true);
    $(elem).append(newval).trigger("change");
}

function hook_select2_hint(elem: HTMLSelectElement, source_id: string) {
    const source_field = $(source_id);
    if (!source_field) return;
    set_select2_element(elem, String(source_field.val() ?? "")); // page initialization
    source_field.on("change", () =>
        set_select2_element(elem, String(source_field.val() ?? "")),
    );
}

function ajax_autocomplete_request(
    value: string,
    elem: HTMLSelectElement,
    autocompleter: AutoCompleter,
) {
    const callback: (autocompleter: any, elem: HTMLSelectElement) => any =
        dynamicParamsCallbacks[
            autocompleter.dynamic_params_callback_name || "nop"
        ];
    return (
        "request=" +
        encodeURIComponent(
            JSON.stringify({
                ident: autocompleter.ident,
                params: callback(autocompleter, elem),
                value: value,
            }),
        )
    );
}

function select2_ajax_vs_autocomplete(
    elem: HTMLSelectElement,
    autocompleter: AutoCompleter,
) {
    const value: (term: QueryOptions) => string = term =>
        term.term !== undefined
            ? term.term
            : ["hostname", "service", "label"].find(el =>
                    autocompleter.ident.includes(el),
                )
              ? elem.options[elem.selectedIndex]?.innerText || ""
              : "";

    return {
        url: "ajax_vs_autocomplete.py",
        delay: 250,
        type: "POST",
        data: (term: QueryOptions) =>
            ajax_autocomplete_request(value(term), elem, autocompleter),
        processResults: (resp: AutoCompleteAjaxResponse) => {
            return {
                results: resp.result.choices.map(x => ({
                    id: x[0],
                    text: x[1],
                    disabled: x[0] === null, // Reached max limit message non selectable
                })),
            };
        },
    };
}

function select2_vs_autocomplete(
    container: JQuery<Document> | HTMLElement | HTMLDocument,
) {
    $(container)
        .find<HTMLSelectElement>("select.ajax-vals")
        .not(".vlof_prototype .ajax-vals")
        .each((_i: number, elem: HTMLSelectElement) => {
            if (!elem.dataset.autocompleter) return;
            const autocompleter = JSON.parse(elem.dataset.autocompleter);
            // TODO: move placeholder_title to python autocompleter config!
            const field_element =
                [
                    "hostname",
                    "service",
                    "metric",
                    "graph",
                    "label",
                    "dashboard",
                    "report",
                ].find(el => autocompleter.ident.includes(el)) || "item";
            let placeholder_title = `(Select ${field_element})`;
            if (autocompleter.ident === "wato_folder_choices")
                placeholder_title = "(Select target folder)";

            $(elem)
                .select2({
                    width: "style",
                    allowClear: true,
                    placeholder: placeholder_title,
                    ajax: select2_ajax_vs_autocomplete(elem, autocompleter),
                    templateResult: format_select2_item,
                    templateSelection: format_select2_item,
                })
                .on("select2:open", () => {
                    if (
                        ["hostname", "service", "label"].includes(field_element)
                    )
                        $(".select2-search input").val(elem.value);
                });

            if (elem.id.endsWith("_hostname_hint"))
                hook_select2_hint(elem, "#context_host_p_host");

            if (elem.id.endsWith("_service_hint"))
                hook_select2_hint(elem, "#context_service_p_service");

            // CustomGraph editor clearing
            if (elem.id.endsWith(`_metric_${field_element}_hint`)) {
                const tail = field_element.length + 6;
                const metric_field_id = `#${elem.id.slice(0, -tail)}`;
                $(elem).on("change.select2", () => {
                    $(metric_field_id).empty();
                    if (field_element === "hostname")
                        $(metric_field_id + "_service_hint").empty();
                });
            }

            // Query set value. Horrible Select2 default options query
            if (elem.value !== "") {
                const term = elem.value;
                $.ajax({
                    type: "POST",
                    url: "ajax_vs_autocomplete.py",
                    data: ajax_autocomplete_request(term, elem, autocompleter),
                }).then((data: AutoCompleteAjaxResponse) => {
                    const pick = data.result.choices.find(el => el[0] === term);
                    if (pick) {
                        const option = new Option(pick[1], pick[0], true, true);
                        $(elem).empty().append(option);
                    }
                });
            }
        });
}

export function initialize_autocompleters(
    container: JQuery<Document> | HTMLElement | HTMLDocument,
) {
    select2_vs_autocomplete(container);
}

//TODO change any after fixing colorpicker problem
//colorpicker functionalities are copied into a
// js file instead of being used through package.json
//and i think it can't be used as an npm dependency
//see :https://github.com/DavidDurman/FlexiColorPicker
//so we should either use another package or find another solution
const vs_color_pickers: Record<string, any> = {};

export function add_color_picker(varprefix: string, value: string) {
    vs_color_pickers[varprefix] = ColorPicker(
        document.getElementById(varprefix + "_picker"),
        function (hex: string) {
            update_color_picker(varprefix, hex, false);
        },
    );

    querySelectorID<HTMLInputElement>(varprefix + "_input")!.oninput =
        function () {
            //@ts-ignore
            update_color_picker(varprefix, this["value"], true);
        };

    update_color_picker(varprefix, value, true);
}

function update_color_picker(
    varprefix: string,
    hex: string,
    update_picker: boolean,
) {
    if (!/^#[0-9A-F]{6}$/i.test(hex)) return; // skip invalid/unhandled colors

    querySelectorID<HTMLInputElement>(varprefix + "_input")!.value = hex;
    querySelectorID<HTMLInputElement>(varprefix + "_value")!.value = hex;
    querySelectorID(varprefix + "_preview")!.style.backgroundColor = hex;

    //@ts-ignore
    if (update_picker) vs_color_pickers[varprefix].setHex(hex);
}

export function visual_filter_list_reset(
    varprefix: string,
    page_request_vars: Record<string, any> | undefined,
    page_name: string,
    reset_ajax_page: string,
    context: Record<string, Record<string, string>>,
) {
    const request = {
        varprefix: varprefix,
        page_request_vars: page_request_vars,
        page_name: page_name,
        context: context,
    };
    const post_data = "request=" + encodeURIComponent(JSON.stringify(request));

    call_ajax(reset_ajax_page + ".py", {
        method: "POST",
        post_data: post_data,
        handler_data: {
            varprefix: varprefix,
        },
        response_handler: function (
            _handler_data: {varprefix: string},
            ajax_response: string,
        ) {
            const response = JSON.parse(ajax_response);
            const filters_html = response.result.filters_html;
            const filter_list = document.getElementById(
                varprefix + "_popup_filter_list_selected",
            )!;
            set_inner_html_and_execute_scripts(
                filter_list.getElementsByClassName(
                    "simplebar-content",
                )[0] as HTMLElement,
                filters_html,
            );
            add_simplebar_scrollbar(varprefix + "_popup_filter_list");
            listofmultiple_disable_selected_options(varprefix);
            enable_dynamic_form_elements();
        },
    });

    // Disable the reset button
    const reset_button = document.getElementById(
        varprefix + "_reset",
    ) as HTMLButtonElement;
    reset_button.disabled = true;
}

function set_inner_html_and_execute_scripts(elm: HTMLElement, html: string) {
    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
    elm.innerHTML = html;

    for (const original_script of elm.getElementsByTagName("script")) {
        if (!original_script.hasAttribute("data-cmk_execute_after_replace"))
            continue;

        const new_script: HTMLScriptElement = document.createElement("script");

        for (const attr of original_script.attributes) {
            new_script.setAttribute(attr.name, attr.value);
        }

        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        new_script.innerHTML = original_script.innerHTML;
        original_script.parentNode!.replaceChild(new_script, original_script);
    }
}

export function update_unit_selector(selectbox: string, metric_prefix: string) {
    const change_unit_to_match_metric = (
        metric: string | number | string[] | undefined,
    ) => {
        const post_data =
            "request=" + encodeURIComponent(JSON.stringify({metric: metric}));
        call_ajax("ajax_vs_unit_resolver.py", {
            method: "POST",
            post_data: post_data,
            response_handler: (_indata: any, response: string) => {
                const json_data = JSON.parse(response);
                // Error handling is: If request failed do nothing
                if (json_data.result_code == 0)
                    $("#" + selectbox + "_sel")
                        .val(json_data.result.unit_choice_index)
                        .trigger("change");
            },
        });
    };
    const metric_selector = $("#" + metric_prefix);
    const metric_selected = metric_selector.val();
    // Only update unit info if no metric was selected before. This honors
    // changed values in the unit section. Otherwise the default unit will
    // always be set on editing a Gauge dashlet or the Metric history painter.
    if (metric_selected === null) {
        change_unit_to_match_metric(metric_selected);
    }
    metric_selector.on("change", event =>
        change_unit_to_match_metric((event.target as HTMLOptionElement).value),
    );
}

export function fetch_ca_from_server(varprefix: string) {
    const address = document.querySelector<HTMLInputElement>(
        `input[name='${varprefix + "_address"}']`,
    )!.value;
    const port = document.querySelector<HTMLInputElement>(
        `input[name='${varprefix + "_port"}']`,
    )!.value;

    call_ajax("ajax_fetch_ca.py", {
        method: "POST",
        post_data:
            "address=" +
            encodeURIComponent(address) +
            "&port=" +
            encodeURIComponent(port),
        response_handler: (_data: any, ajax_response: string) => {
            const response = JSON.parse(ajax_response);

            const status = document.getElementById(
                varprefix + "_status",
            ) as HTMLInputElement;
            const content = document.querySelector<HTMLTextAreaElement>(
                `textarea[name='${varprefix}']`,
            )!;
            if (response.result_code !== 0) {
                /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
                status.innerText = response.result;
                content.value = "";
            } else {
                /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
                status.innerHTML = response.result.summary;
                content.value = response.result.cert_pem;
            }
        },
    });
}

export function single_label_on_change(select_elem: HTMLSelectElement) {
    if (select_elem.value === "") {
        return;
    }

    // The current select2 needs to be closed before the new one may be opened properly.
    // This seems to be a select2 bug. Otherwise, the new one is opened without focus, which makes
    // a click necessary before typing
    $(select_elem).select2("close");
    const tbody: HTMLTableSectionElement = select_elem.closest("tbody")!;
    const labels = tbody.getElementsByClassName(
        "label",
    ) as HTMLCollectionOf<HTMLSelectElement>;

    // If the last select.label within tbody has a non empty value, add a new row
    if (labels[labels.length - 1].value !== "") {
        const add_element_button = select_elem
            .closest("div.valuespec_listof")!
            .getElementsByClassName("vlof_add_button")![0] as HTMLAnchorElement;
        add_element_button.click();
    }

    // Let the new bool dropdown default to the value of the last one
    const new_row = tbody.children[tbody.children.length - 1]!;
    const last_bool_elem = document.getElementById(
        select_elem.id.replace(/_vs$/, "_bool"),
    ) as HTMLSelectElement;
    const new_bool_elem = document.getElementById(
        new_row.id.replace("vs_entry", "vs") + "_bool",
    ) as HTMLSelectElement;
    new_bool_elem.value = last_bool_elem.value;
    enable_select2_dropdowns(new_row as HTMLElement);

    // Automatically open (and focus) the newly added select2 element
    const new_vs_select_id = new_bool_elem.id.replace(/_bool$/, "_vs");
    $("#" + new_vs_select_id).select2("open");
}

export function toggle_label_row_opacity(
    elem: HTMLSelectElement,
    is_active: boolean,
) {
    const tr: HTMLTableRowElement = elem.closest("tr")!;
    const tbody: HTMLTableSectionElement = tr.closest("tbody")!;
    if (tbody.lastChild !== tr) return;

    if (is_active) {
        add_class(tr, "active");
    } else {
        remove_class(tr, "active");
    }
}

export function label_group_delete(
    varprefix: string,
    index: string,
    first_elem_choices_or_label: [string, string][] | string,
    show_empty_group_by_default: boolean,
) {
    const tr = document.getElementById(
        varprefix + "_entry_" + index,
    )! as HTMLTableRowElement;
    const tbody = tr.parentNode as HTMLTableSectionElement;

    if (tbody.children[0] === tr) {
        // The tr to be deleted is the first child -> put in first element specific choices/label
        if (tbody.children.length == 1 && show_empty_group_by_default) {
            // Add another element if the one to be deleted is the only one and if an empty group
            // must be shown by default
            const add_element_buttons = tbody
                .closest("div.valuespec_listof")!
                .getElementsByClassName("vlof_add_button") as HTMLCollection;
            const add_element_button = add_element_buttons[
                add_element_buttons.length - 1
            ] as HTMLAnchorElement;
            add_element_button.click();
        }

        if (tbody.children.length > 1) {
            const next_row_select: HTMLSelectElement = tbody.children[1]
                .getElementsByClassName("bool")![0]
                .getElementsByTagName("select")![0];
            if (typeof first_elem_choices_or_label !== "string") {
                // first element has dropdown choices -> adjust the dropdown choices
                const first_elem_choices: Record<string, string> =
                    Object.fromEntries(first_elem_choices_or_label);
                const options: HTMLOptionsCollection = next_row_select.options;
                for (let i = 0; i < options.length; i++) {
                    if (
                        Object.prototype.hasOwnProperty.call(
                            first_elem_choices,
                            options[i].value,
                        )
                    ) {
                        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
                        options[i].innerHTML =
                            first_elem_choices[options[i].value];
                    } else {
                        options.remove(i);
                        i -= 1;
                    }
                }
            } else {
                // first element has a label -> remove dropdown and put in a label span with hidden
                // input for the boolean
                const next_bool_div =
                    next_row_select.parentNode as HTMLDivElement;
                const hidden_input = document.getElementsByName(
                    varprefix + "_" + index + "_bool",
                )![0] as HTMLInputElement;
                hidden_input.name = next_row_select.name;
                next_bool_div.removeChild(next_row_select.nextSibling!); // select2 span
                next_bool_div.removeChild(next_row_select);
                next_bool_div.insertBefore(
                    tr.getElementsByClassName("vs_label")[0],
                    next_bool_div.lastChild,
                );
                next_bool_div.append(hidden_input);
            }
        }
    }

    listof_delete(varprefix, index);
    enable_dynamic_form_elements(tbody);
}

export function init_on_change_validation(
    varname: string,
    filter_ident: string,
) {
    const select = document.getElementById(varname) as HTMLSelectElement;
    if (!select) return;

    $(select).on("change", () => {
        const request: Record<string, string> = {
            filter_ident: filter_ident,
            value: select.value!,
            varname: varname,
        };
        const post_data =
            "request=" + encodeURIComponent(JSON.stringify(request));
        call_ajax("ajax_validate_filter.py", {
            method: "POST",
            post_data: post_data,
            handler_data: {select: select},
            response_handler: function (
                handler_data: {select: HTMLSelectElement},
                ajax_response: string,
            ) {
                const resp = JSON.parse(ajax_response);
                const parent = handler_data.select
                    .parentElement! as HTMLElement;

                // Remove old error msgs
                const errors: HTMLCollection =
                    parent.getElementsByClassName("error");
                for (const e of errors) {
                    e.remove();
                }

                // Show current error
                const error_html: string = resp.result.error_html;
                if (error_html) {
                    const error_div = document.createElement("div");
                    parent.insertBefore(error_div, select);
                    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
                    error_div.outerHTML = resp.result.error_html;
                }
            },
        });
    });
}
