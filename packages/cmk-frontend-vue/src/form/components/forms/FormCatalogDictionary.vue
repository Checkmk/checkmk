<script setup lang="ts">
import type { DictionaryElement } from '@/form/components/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'
import { immediateWatch } from '@/form/components/utils/watch'
import type { ValidationMessages } from '@/form/components/utils/validation'

const props = defineProps<{
  entries: Array<DictionaryElement>
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, unknown>>({ required: true })

immediateWatch(
  () => props.entries,
  (newValue) => {
    newValue.forEach((element) => {
      if (!(element.ident in data.value)) {
        data.value[element.ident] = element.default_value
      }
    })
  }
)
</script>

<template>
  <tr v-for="element in entries" :key="element.ident">
    <td class="legend">
      <div class="title">
        {{ element.parameter_form.title }}
        <span
          class="dots"
          :class="{
            required: element.required
          }"
          >{{ Array(200).join('.') }}</span
        >
      </div>
    </td>
    <td class="content">
      <FormEdit
        v-model:data="data[element.ident]!"
        :backend-validation="backendValidation"
        :spec="element.parameter_form"
      />
    </td>
  </tr>
</template>
