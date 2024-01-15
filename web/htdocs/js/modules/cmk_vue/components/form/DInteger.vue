<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {VueComponentSpec} from "cmk_vue/types";
import ValidationError from "cmk_vue/components/ValidatonError.vue";

const emit = defineEmits<{
    (e: "update-value", value: any): void;
}>();
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

onMounted(() => {
    component_value.value = props.component.config.value.toString();
    send_value_upstream(component_value.value);
});

function send_value_upstream(new_value: string) {
    emit("update-value", parseInt(new_value));
}

let unit = computed(() => {
    return props.component.config.unit || "";
});

let style = computed(() => {
    return {width: "5.8ex"};
});
</script>

<template>
    <input
        class="number"
        :style="style"
        type="text"
        :value="component_value"
        @input="send_value_upstream($event.target.value)"
        :placeholder="component.config.placeholder"
    />
    <span v-if="unit" class="vs_floating_text">{{ unit }}</span>
    <ValidationError :component="component"></ValidationError>
</template>
