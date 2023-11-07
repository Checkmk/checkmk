<script setup lang="ts">
import {VueComponentSpec} from "cmk_vue/types";

const props = defineProps<{
    component: VueComponentSpec;
}>();
</script>

<template>
    <label
        style="background: #dc5e5e"
        v-if="component.validation_errors?.length > 0"
    >
        {{ component.validation_errors[0] }}
    </label>
</template>
