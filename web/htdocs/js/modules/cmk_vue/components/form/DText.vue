<script setup lang="ts">
import {ref, computed, onMounted, onUpdated} from "vue";
import {VueComponentSpec} from "cmk_vue/types";
import ValidationError from "cmk_vue/components/ValidatonError.vue";

const emit = defineEmits<{
    (e: "update-value", value: any): void;
}>();

function send_value_upstream(new_value: any) {
    emit("update-value", parseInt(new_value));
}

interface VueTextComponentSpec extends VueComponentSpec {
    config: {
        value: string;
        placeholder?: string;
    };
}

const props = defineProps<{
    component: VueTextComponentSpec;
}>();

const component_value = ref<string>();

onMounted(() => {
    // console.log("mounted text")
    component_value.value = props.component.config.value;
    send_value_upstream(component_value.value);
});

onUpdated(() => {
    console.log("updated text");
});

let style = computed(() => {
    return {width: "25.8ex"};
});
</script>

<template>
    <input
        :style="style"
        type="text"
        v-model="component_value"
        @input="send_value_upstream($event.target.value)"
        :placeholder="component.config.placeholder"
    />
    <ValidationError :component="component"></ValidationError>
</template>
