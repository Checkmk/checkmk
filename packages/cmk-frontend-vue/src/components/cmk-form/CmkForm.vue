<script setup lang="ts">
import { ref } from 'vue'
import { type VueFormSpec } from '@/types'
import CmkFormDispatcher from './CmkFormDispatcher.vue'

defineProps<{
  formSpec: VueFormSpec<unknown>
}>()

let raw_value = ref<unknown>('')
let value_as_json = ref('')

function update_value(new_value: unknown) {
  // console.log('got new value', new_value);
  raw_value.value = new_value
  value_as_json.value = JSON.stringify(new_value)
}
</script>

<template>
  <table class="nform">
    <tr>
      <td>
        <CmkFormDispatcher
          :vue-schema="formSpec.vue_schema"
          :data="formSpec.data"
          @update-value="update_value"
        />
      </td>
    </tr>
    <!-- This input field contains the computed json value which is sent when the form is submitted -->
    <input v-model="value_as_json" :name="formSpec.id" type="hidden" />
  </table>
  <pre>{{ raw_value }}</pre>
</template>
