<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import CmkFormDispatcher from './CmkFormDispatcher.vue'
import type { FormSpec } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/utils'
import type { IComponent } from '@/types'

defineProps<{
  id: string
  spec: FormSpec
}>()

const data = defineModel<unknown>('data', { required: true })
const value_as_json = computed(() => {
  return JSON.stringify(data.value)
})

const component_ref = ref<IComponent>()
function setValidation(validation: ValidationMessages) {
  nextTick(() => {
    component_ref.value!.setValidation(validation)
  })
}

defineExpose({
  setValidation
})
</script>

<template>
  <table class="nform">
    <tr>
      <td>
        <CmkFormDispatcher ref="component_ref" v-model:data="data" :spec="spec" />
      </td>
    </tr>
    <!-- This input field contains the computed json value which is sent when the form is submitted -->
    <input v-model="value_as_json" :name="id" type="hidden" />
  </table>
  <pre>{{ data }}</pre>
</template>
