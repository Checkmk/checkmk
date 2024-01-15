<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {ref} from "vue";
import DInteger from "./DInteger.vue";
import DFloat from "./DInteger.vue";
import {IComponent, VueComponentSpec} from "cmk_vue/types";
import DList from "cmk_vue/components/form/DList.vue";

import {onBeforeMount, onMounted} from "vue";
import DDictionary from "cmk_vue/components/form/DDictionary.vue";
import DDropdownChoice from "cmk_vue/components/form/DDropdownChoice.vue";
import DLegacyValueSpec from "cmk_vue/components/form/DLegacyValueSpec.vue";
import DCheckbox from "cmk_vue/components/form/DCheckbox.vue";
import DCascadingDropdownChoice from "cmk_vue/components/form/DCascadingDropdownChoice.vue";
import DPercentage from "cmk_vue/components/form/DPercentage.vue";
import DListOf from "cmk_vue/components/form/DListOf.vue";
import DText from "cmk_vue/components/form/DText.vue";

const emit = defineEmits<{
    (e: "update-value", value: any): void;
}>();

onBeforeMount(() => {
    console.log("DFORM before mount", props.component);
});

onMounted(() => {
    console.log("DFORM mounted", props.component);
});

const props = defineProps<{
    component: VueComponentSpec;
}>();

// https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: {[name: string]: IComponent} = {
    integer: DInteger,
    float: DFloat,
    percentage: DPercentage,
    text: DText,
    list: DList,
    list_of: DListOf,
    dictionary: DDictionary,
    legacy_valuespec: DLegacyValueSpec,
    checkbox: DCheckbox,
    dropdown_choice: DDropdownChoice,
    cascading_dropdown_choice: DCascadingDropdownChoice,
};

function get_component(): IComponent {
    console.log("get component", props.component.component_type);
    return components[props.component.component_type];
}

function forward_value_upstream(new_value: any) {
    console.log("forward value", props.component.component_type, new_value);
    emit("update-value", new_value);
}
</script>

<template>
    <component
        v-bind:is="get_component()"
        :component="component"
        @update-value="forward_value_upstream"
    >
    </component>
</template>
