<script setup lang="ts">
import {VueComponentSpec} from "cmk_vue/types";

import {ref, onMounted} from "vue";

interface VueCheckboxComponentSpec extends VueComponentSpec {
    config: {
        value: boolean;
        label: string;
    };
}
const props = defineProps<{
    component: VueCheckboxComponentSpec;
}>();

const value = ref(true);

function collect(): any {
    return value.value;
}

function debug_info(): void {
    console.log("Checkbox input", props.component.config.label, value.value);
}

onMounted(() => {
    value.value = props.component.config.value;
});

defineExpose({
    collect,
    debug_info,
});
</script>
<template>
    <div class="container">
        <input
            class="vue_checkbox"
            type="checkbox"
            v-model="value"
            onclick="console.log('boom')"
        />
        <label>{{ component.config.label }}</label>
    </div>
</template>
