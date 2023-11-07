<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {ref} from "vue";
import DNumberInput from "./DNumberInput.vue";
import {IComponent, VueComponentSpec} from "cmk_vue/types";
import DList from "cmk_vue/components/form/DList.vue";

import {onBeforeMount, onMounted} from "vue";
import DDictionary from "cmk_vue/components/form/DDictionary.vue";
import DLegacyValueSpec from "cmk_vue/components/form/DLegacyValueSpec.vue";
import DCheckbox from "cmk_vue/components/form/DCheckbox.vue";

onBeforeMount(() => {
    console.log("DFORM before mount");
});

onMounted(() => {
    console.log("DFORM mounted", props.component);
});

const props = defineProps<{
    component: VueComponentSpec;
}>();

// https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: {[name: string]: IComponent} = {
    number: DNumberInput,
    list: DList,
    dictionary: DDictionary,
    legacy_valuespec: DLegacyValueSpec,
    checkbox: DCheckbox,
};

const embedded_component = ref<IComponent>();

function collect(): any {
    if (embedded_component.value == null) {
        console.log("can not collect for", props.component.component_type);
        return null;
    }
    return embedded_component.value.collect();
}

function debug_info(): string {
    if (embedded_component.value == null) return;
    embedded_component.value.debug_info();
}

function get_component(): IComponent {
    return components[props.component.component_type];
}

defineExpose({
    collect,
    debug_info,
});
</script>

<template>
    <div class="d-form">
        <component
            v-bind:is="get_component()"
            :component="component"
            ref="embedded_component"
        >
        </component>
    </div>
</template>
