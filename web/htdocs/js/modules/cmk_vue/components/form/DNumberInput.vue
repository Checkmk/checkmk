<script setup lang="ts">
import {ref, computed, onMounted} from "vue";
import {VueComponentSpec} from "cmk_vue/types";
import ValidationError from "cmk_vue/components/ValidatonError.vue";

interface VueLegacyNumberComponentSpec extends VueComponentSpec {
    config: {
        value: number;
        unit?: string;
        placeholder?: string;
    };
}

const props = defineProps<{
    component: VueLegacyNumberComponentSpec;
}>();

const component_value = ref<string>();

function debug_info() {
    console.log("Number input", props.component.title);
}

onMounted(() => {
    component_value.value = props.component.config.value.toString();
});

let unit = computed(() => {
    return props.component.config.unit || "";
});

let style = computed(() => {
    return {width: "5.8ex"};
});

function collect(): number {
    if (component_value.value == null)
        // TODO: may throw "required" exception, and blocks sending of form
        return 0;
    return parseInt(component_value.value);
}

defineExpose({
    collect,
    debug_info,
});
</script>

<template>
    <!--  <div>{{component}}</div>-->
    <input
        class="number"
        :style="style"
        type="text"
        v-model="component_value"
        :placeholder="component.config.placeholder"
    />
    <span v-if="unit" class="vs_floating_text">{{ unit }}</span>
    <ValidationError :component="component"></ValidationError>
</template>
