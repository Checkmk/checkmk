<script setup lang="ts">
import { computed } from 'vue'
import CmkFormDispatcher from './CmkFormDispatcher.vue'
import type { FormSpec } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/utils'

defineProps<{
  id: string
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })
const value_as_json = computed(() => {
  return JSON.stringify(data.value)
})
</script>

<template>
  <table class="nform">
    <tr>
      <td>
        <CmkFormDispatcher
          v-model:data="data"
          :backend-validation="backendValidation"
          :spec="spec"
        />
      </td>
    </tr>
    <!-- This input field contains the computed json value which is sent when the form is submitted -->
    <input v-model="value_as_json" :name="id" type="hidden" />
  </table>
  <pre>{{ data }}</pre>
</template>
