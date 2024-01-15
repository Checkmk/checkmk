<script setup lang="ts">
import {onMounted, ref, onBeforeMount} from "vue";
import {IComponent, VueComponentSpec} from "cmk_vue/types";
import DForm from "./DForm.vue";
import {clicked_checkbox_label} from "cmk_vue/utils";

const emit = defineEmits<{
    (e: "update-value", value: any): void;
}>();

interface VueDictionaryElement {
    name: string;
    required: boolean;
    is_active: boolean;
    component: VueComponentSpec;
}

interface VueDictionaryComponentSpec extends VueComponentSpec {
    config: {
        elements: VueDictionaryElement[];
    };
}

const props = defineProps<{
    component: VueDictionaryComponentSpec;
}>();

let component_value: {[name: string]: any} = {};
const element_components = ref<{[index: string]: IComponent}>({});
const element_active: {[index: string]: any} = ref({});

onBeforeMount(() => {
    component_value = {};
    props.component.config.elements.forEach(element => {
        if (element.is_active)
            component_value[element.name] = element.component.config.value;
    });
});
onMounted(() => {
    props.component.config.elements.forEach(element => {
        if (element.is_active || element.required)
            element_active.value[element.name] = true;
    });
    emit("update-value", component_value);
});
function get_elements_from_props(): VueDictionaryElement[] {
    return props.component.config.elements;
}

function update_key(key: string, new_value: any) {
    component_value[key] = new_value;
    emit("update-value", component_value);
}

function clicked_dictionary_checkbox_label(event: MouseEvent, key: string) {
    let target = event.target;
    if (!target) return;
    clicked_checkbox_label(target as HTMLLabelElement);
    component_value[key] = undefined;
    emit("update-value", component_value);
}
</script>

<template>
    <table class="dictionary">
        <tbody>
            <tr
                v-for="element in get_elements_from_props()"
                v-bind:key="element.name"
            >
                <td class="dictleft">
                    <span class="checkbox">
                        <input
                            type="checkbox"
                            v-model="element_active[element.name]"
                            v-if="!element.required"
                        />
                        <label
                            :onclick="
                                event =>
                                    clicked_dictionary_checkbox_label(
                                        event,
                                        element.name
                                    )
                            "
                        >
                            {{ element.component.title }}
                        </label>
                    </span>
                    <br />
                    <div class="dictelement indent">
                        <DForm
                            v-if="element_active[element.name]"
                            :component="element.component"
                            :ref="
                                el => {
                                    element_components[element.name] = el;
                                }
                            "
                            @update-value="
                                new_value => update_key(element.name, new_value)
                            "
                        />
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</template>
