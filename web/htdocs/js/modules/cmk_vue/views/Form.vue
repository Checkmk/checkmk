<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {ref} from "vue";
import {VueComponentSpec, VueFormSpec} from "cmk_vue/types";
import DForm from "../components/form/DForm.vue";

const props = defineProps<{
    form_spec: VueFormSpec;
}>();

const computed_value: any = ref(null);
const dForm: DForm | null = ref(null);

function update_form_field(): void {
    let value = null;
    if (dForm != null && dForm.value) {
        value = dForm.value.collect();
    }
    computed_value.value = JSON.stringify(value);
}

function get_root_component(): VueComponentSpec {
    return props.form_spec.component;
}

defineExpose({
    update_form_field,
});
</script>

<template>
    <table class="nform">
        <tr>
            <td><DForm :component="get_root_component()" ref="dForm" /></td>
        </tr>
        <!-- This input field contains the computed json value which is sent when the form is submitted -->
        <input :name="form_spec.id" type="hidden" v-model="computed_value" />
    </table>
</template>
