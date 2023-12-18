<script setup lang="ts">
import {IComponent, VueComponentSpec} from "cmk_vue/types";
import * as d3 from "d3";

import {ref, onBeforeMount, onMounted, onUpdated, nextTick} from "vue";
import DForm from "./DForm.vue";
import {D3DragEvent} from "d3";

const emit = defineEmits<{
    (e: "update-value", value: any): void;
}>();
interface VueListOfComponentSpec extends VueComponentSpec {
    config: {
        template: VueComponentSpec;
        add_text: string;
        elements: VueComponentSpec[];
    };
    uuid?: string; // Added within this component (does not modifiy props)
}

const props = defineProps<{
    component: VueListOfComponentSpec;
}>();

const class_listof_element = "listof_element";
const class_element_dragger = "element_dragger";
let table_ref = ref<HTMLTableElement | null>(null);

let component_value: {[uuid: string]: any} = {};
const element_components: {[uuid: string]: IComponent} = {};
const dynamic_elements = ref<VueComponentSpec[]>([]);

const component_key = ref(0);

onBeforeMount(() => {
    const initial_elements: VueComponentSpec[] = [];
    props.component.config.elements.forEach(element => {
        let copy = JSON.parse(JSON.stringify(element));
        copy.uuid = crypto.randomUUID();
        initial_elements.push(copy);
    });
    dynamic_elements.value = initial_elements;
});

onMounted(() => {
    // dynamic_elements.value = computed_list();
    setup_drag_handler();
    force_update();
});

onUpdated(() => {
    setup_drag_handler();
});

let dragged_row: HTMLTableRowElement | null = null;
function get_dragged_row(
    event: D3DragEvent<HTMLImageElement, null, HTMLImageElement>
) {
    if (!event.sourceEvent.target) return;
    const target = event.sourceEvent.target;
    return target.closest("tr");
}

function drag_start(event: DragEvent) {
    dragged_row = get_dragged_row(event) as HTMLTableRowElement;
    d3.select(dragged_row).classed("dragging", true);
}
function dragging(event: MouseEvent) {
    if (dragged_row == null) return;
    const y_coords = d3.pointer(event)[1];

    function sibling_middle_point(sibling: Element) {
        let sibling_rect = sibling.getBoundingClientRect();
        return sibling_rect.top + sibling_rect.height / 2;
    }

    let previous = dragged_row.previousElementSibling;
    while (previous && y_coords < sibling_middle_point(previous)) {
        table_ref.value.insertBefore(dragged_row, previous);
        previous = dragged_row.previousElementSibling;
    }

    let next = dragged_row.nextElementSibling;
    while (next && y_coords > sibling_middle_point(next)) {
        table_ref.value.insertBefore(dragged_row, next.nextElementSibling);
        next = dragged_row.nextElementSibling;
    }
}
function drag_end(
    event: D3DragEvent<HTMLImageElement, null, HTMLImageElement>
) {
    d3.selectAll("tr.listof_element").classed("dragging", false);
    force_update();
}

function setup_drag_handler() {
    const drag_handler = d3
        .drag<HTMLTableRowElement, null>()
        .on("start.drag", event => drag_start(event))
        .on("drag.drag", event => dragging(event))
        .on("end.drag", event => drag_end(event));
    const elements = d3
        .select(table_ref.value)
        .selectChildren<HTMLTableRowElement, null>("tr")
        .selectChildren<HTMLTableCellElement, null>("td.vlof_buttons")
        .select<HTMLImageElement>("img." + class_element_dragger);
    elements.call(drag_handler);
}

function force_update() {
    console.log("force update");
    component_key.value += 1;
    update_actual_value();
}

function add_element() {
    console.log("add listof element");
    let new_element = JSON.parse(
        JSON.stringify(props.component.config.template)
    );
    new_element.uuid = crypto.randomUUID();
    dynamic_elements.value.push(new_element);
}

function remove_element(element: VueListOfComponentSpec) {
    event.preventDefault();
    delete element_components[element.uuid || -1];
    delete component_value[element.uuid || -1];
    dynamic_elements.value.splice(dynamic_elements.value.indexOf(element), 1);
    nextTick(() => {
        update_actual_value();
    });
}

function update_list_value(uuid: string, new_value: any) {
    component_value[uuid] = new_value;
    update_actual_value();
}

function update_actual_value() {
    const table = table_ref.value;
    if (table == null) return;
    let actual_value: any[] = [];
    table
        .querySelectorAll(":scope > tr." + class_listof_element)
        .forEach(child_node => {
            actual_value.push(
                component_value[child_node.attributes.uuid.value]
            );
        });
    emit("update-value", actual_value);
}
</script>

<!--TODO: fix theme specific icons / fix hardcoded text-->
<template ref="table_dom">
    <table class="valuespec_listof" ref="table_ref">
        <tr
            :key="element.uuid"
            v-for="element in dynamic_elements"
            :class="class_listof_element"
            :uuid="element.uuid"
        >
            <td class="vlof_buttons">
                <a
                    ><img
                        src="themes/modern-dark/images/icon_drag.svg"
                        :class="class_element_dragger"
                /></a>
                <a title="Delete this entry">
                    <img
                        class="icon iconbutton"
                        @click.prevent="remove_element(element)"
                        src="themes/modern-dark/images/icon_close.svg"
                    />
                </a>
            </td>
            <td class="vlof_content">
                <DForm
                    :component="element"
                    :ref="
                        el => {
                            console.log('add ref', el);
                            if (el != null) {
                                element_components[element.uuid] = el;
                            }
                        }
                    "
                    @update-value="
                        new_value => update_list_value(element.uuid, new_value)
                    "
                />
            </td>
        </tr>
    </table>
    <br />
    <input
        type="button"
        class="button"
        @click.prevent="add_element"
        :value="component.config.add_text"
    />
</template>

<DForm
    :component="element"
    :ref="
        el => {
            if (el != null) {
                element_components[element.uuid] = el;
            }
        }
    "
    @update-value="new_value => update_list_value(element.uuid, new_value)"
/>
