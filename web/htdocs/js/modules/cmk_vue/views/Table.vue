<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {TableRow, VueTableSpec} from "cmk_vue/types";
import {computed, ref, onMounted, onBeforeUpdate, onUpdated} from "vue";
import crossfilter, {Crossfilter} from "crossfilter2";
import * as d3 from "d3";

const props = defineProps<{
    table_spec: VueTableSpec;
}>();

const search_text = ref<string>("");
const force_render = ref(0);

const row_crossfilter = crossfilter<TableRow>();
const search_text_dimension = row_crossfilter.dimension<string>(
    (d: TableRow) => {
        let combined_text: string[] = [];
        d.columns.forEach(column => {
            column.content.forEach(content => {
                // Might add additional types to this data dimension
                if (content.type == "text")
                    combined_text.push(content.content.toLowerCase());
            });
        });
        return combined_text.join("#");
    }
);

function replace_inpage_search() {
    const search_form = d3.select("#form_inpage_search_form");
    search_form.selectAll("input:not(.text)").remove();
    search_form.selectAll("input").on("keyup", event => {
        search_text.value = event.target.value;
    });
}

function get_rows() {
    const search_value = search_text.value.toLowerCase();

    const use_crossfilter = true;
    let records: TableRow[];
    if (!use_crossfilter) {
        records = [];
        props.table_spec.rows.forEach(row => {
            let found_match = false;
            row.columns.forEach(columns => {
                columns.content.forEach(content => {
                    if (
                        content.type == "text" &&
                        content.content.includes(search_value)
                    ) {
                        found_match = true;
                    }
                });
            });
            if (found_match) records.push(row);
        });
    } else {
        function get_custom_filter(search_text: string) {
            return function customFilter(value: string) {
                return value.includes(search_text);
            };
        }
        search_text_dimension.filterFunction(get_custom_filter(search_value));
        records = row_crossfilter.allFiltered();
    }

    function get_custom_sorter_function(index: number, direction) {
        return function (a: TableRow, b: TableRow) {
            const a_content = a.columns[index].content[0].content.toLowerCase();
            const b_content = b.columns[index].content[0].content.toLowerCase();
            if (a_content == b_content) return 0;
            if (a_content > b_content) return direction;
            return -direction;
        };
    }

    if (current_sort_index != null) {
        records.sort(
            get_custom_sorter_function(
                current_sort_index[0],
                current_sort_index[1]
            )
        );
    }
    return records;
}

onMounted(() => {
    row_crossfilter.add(props.table_spec.rows);
    force_render.value += 1;
    replace_inpage_search();
});

let update_start = 0;

onBeforeUpdate(() => {
    update_start = performance.now();
});

onUpdated(() => {
    console.log("Update took ", performance.now() - update_start);
});

let current_sort_index: null | [number, number] = null;
function set_sort_index(index: number) {
    if (current_sort_index == null || current_sort_index[0] != index)
        current_sort_index = [index, 1];
    else if (current_sort_index[0] == index)
        current_sort_index = [index, current_sort_index[1] * -1];
    force_render.value += 1;
}
</script>

<template>
    <label>VUE Table</label>
    <table :key="force_render" :class="table_spec.classes">
        <tbody>
            <tr>
                <th
                    v-for="(header, index) in table_spec.headers"
                    v-on:click="set_sort_index(index)"
                >
                    {{ header }}
                </th>
            </tr>

            <tr :key="row.key" v-for="row in get_rows()" :class="row.classes">
                <td v-for="cell in row.columns" :class="cell.classes">
                    <template v-for="content in cell.content">
                        <input
                            v-if="content.type === 'checkbox'"
                            class="vue_checkbox"
                            type="checkbox"
                        />
                        <a
                            v-if="content.type === 'button'"
                            :href="content.url"
                            :title="content.title"
                        >
                            <img class="icon iconbutton" :src="content.icon" />
                        </a>
                        <span v-if="content.type === 'text'">{{
                            content.content
                        }}</span>
                        <span
                            v-if="content.type === 'html'"
                            v-html="content.html_content"
                        />
                        <a v-if="content.type === 'href'" :href="content.url">{{
                            content.alias
                        }}</a>
                    </template>
                </td>
            </tr>
        </tbody>
    </table>
</template>
