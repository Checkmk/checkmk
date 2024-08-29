<script setup lang="ts">
import type * as FormSpec from '@/form/components/vue_formspec_components'
import {
  groupIndexedValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'
import FormEdit from '@/form/components/FormEdit.vue'
import { ref, watch } from 'vue'
import FormValidation from '@/form/components/FormValidation.vue'

const props = defineProps<{
  spec: FormSpec.Tuple
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown[]>('data', { required: true })

const validation = ref<Array<string>>([])

type ElementIndex = number
const elementValidation = ref<Record<ElementIndex, ValidationMessages>>({})

watch(
  [() => props.backendValidation],
  ([newBackendValidation]) => {
    setValidation(newBackendValidation)
  },
  { immediate: true }
)

function setValidation(newBackendValidation: ValidationMessages) {
  const [_tupleValidations, _elementValidations] = groupIndexedValidations(
    newBackendValidation,
    props.spec.elements.length
  )
  validation.value = _tupleValidations
  elementValidation.value = _elementValidations
}

function capitalizeFirstLetter(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}
</script>

<template>
  <table
    v-if="spec.layout == 'horizontal' || spec.layout == 'horizontal_titles_top'"
    class="valuespec_tuple horizontal"
  >
    <tr>
      <template v-for="(element, index) in spec.elements" :key="index">
        <td class="tuple_td">
          <span v-if="spec.show_titles && element.title" class="title">{{
            capitalizeFirstLetter(element.title)
          }}</span>
          <br v-if="spec.show_titles && element.title && spec.layout == 'horizontal_titles_top'" />
          <span v-else> </span>
          <FormEdit
            v-model:data="data[index]"
            :spec="element"
            :backend-validation="elementValidation[index]!"
          />
        </td>
      </template>
    </tr>
  </table>

  <table v-if="spec.layout == 'vertical'" class="valuespec_tuple vertical">
    <tr v-for="(element, index) in spec.elements" :key="index">
      <td v-if="spec.show_titles" class="tuple_left">
        <span v-if="element.title" class="vs_floating_text">{{
          capitalizeFirstLetter(element.title)
        }}</span>
      </td>
      <td :class="{ tuple_right: true, has_title: element.title }">
        <FormEdit
          v-model:data="data[index]"
          :spec="element"
          :backend-validation="elementValidation[index]!"
        />
      </td>
    </tr>
  </table>

  <template v-if="spec.layout == 'float'">
    <template v-for="(element, index) in spec.elements" :key="index">
      <FormEdit
        v-model:data="data[index]"
        :spec="element"
        :backend-validation="elementValidation[index]!"
      />
    </template>
  </template>
  <FormValidation :validation="validation"></FormValidation>
</template>
