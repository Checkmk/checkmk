<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import { ref, computed } from 'vue'
import { VueComponentSpec, VueFormSpec } from '../types'
import DForm from '@/components/form/DForm.vue'

const props = defineProps<{
  form_spec: VueFormSpec
}>()

let raw_value = ref('')
let value_as_json = ref('')

function update_value(new_value: any) {
  // console.log('got new value', new_value);
  raw_value.value = new_value
  value_as_json.value = JSON.stringify(new_value)
}
</script>

<template>
  <table class="nform">
    <tr>
      <td>
        <DForm @update-value="update_value" :component="form_spec.component" />
      </td>
    </tr>
    <!-- This input field contains the computed json value which is sent when the form is submitted -->
    <input :name="form_spec.id" type="hidden" v-model="value_as_json" />
  </table>
  <pre>{{ raw_value }}</pre>
</template>
