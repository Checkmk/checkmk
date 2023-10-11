<script setup lang="ts">
import {ref} from "vue";
import {IComponent, VueComponentSpec} from "cmk_vue/types";
import DForm from "./DForm.vue";
interface VueListComponentSpec extends VueComponentSpec {
    config: {
        elements: VueComponentSpec[];
    };
}

const props = defineProps<{
    component: VueListComponentSpec;
}>();

const formElements = ref<IComponent[]>([]);

function collect(): any {
    const result: any[] = [];
    get_elements().forEach((element, index) => {
        const form_element = formElements.value[index];
        result.push(form_element.collect());
    });
    return result;
}
function debug_info(): void {
    console.log("List with ", get_elements().length, "elements");
    get_elements().forEach((element, index) => {
        formElements.value[index].debug_info();
    });
}

defineExpose({
    collect,
    debug_info,
});

function get_elements(): VueComponentSpec[] {
    return props.component.config.elements;
}
</script>

<template>
    <!--        <div>DList {{ config }} {{ elements }}</div>-->
    <tr :key="element.index" v-for="(element, index) in get_elements()">
        <td class="tuple_left">
            <span class="vs_floating_text">{{ element.title }}</span>
        </td>
        <td class="tuple_right">
            <DForm
                class="form-listof"
                :component="element"
                :ref="
                    el => {
                        if (el != null) formElements[index] = el;
                    }
                "
            ></DForm>
        </td>
    </tr>
</template>
