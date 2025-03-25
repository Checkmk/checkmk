<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import {
  groupIndexedValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'
import { ref, watch } from 'vue'
import FormValidation from '@/form/components/FormValidation.vue'
import HelpText from '@/components/HelpText.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import { capitalizeFirstLetter } from '@/lib/utils'
import { useFormEditDispatcher } from '@/form/private'
import FormLabel from '@/form/private/FormLabel.vue'

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

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <table
    v-if="spec.layout === 'horizontal' || spec.layout === 'horizontal_titles_top'"
    class="valuespec_tuple horizontal"
  >
    <tbody>
      <tr>
        <template v-for="(element, index) in spec.elements" :key="index">
          <td class="form-tuple__td">
            <FormLabel v-if="spec.show_titles && element.title" class="title">{{
              capitalizeFirstLetter(element.title)
            }}</FormLabel>
            <CmkSpace
              v-if="spec.show_titles && element.title && spec.layout !== 'horizontal_titles_top'"
              size="small"
            />
            <br
              v-if="spec.show_titles && element.title && spec.layout === 'horizontal_titles_top'"
            />
            <FormEditDispatcher
              v-model:data="data[index]"
              :spec="element"
              :backend-validation="elementValidation[index]!"
            />
            <HelpText :help="element.help" />
          </td>
        </template>
      </tr>
    </tbody>
  </table>

  <table v-if="spec.layout === 'vertical'" class="valuespec_tuple vertical">
    <tbody>
      <tr v-for="(element, index) in spec.elements" :key="index">
        <td v-if="spec.show_titles" class="form-tuple__td tuple_left">
          <FormLabel v-if="element.title">{{ capitalizeFirstLetter(element.title) }}</FormLabel>
          <CmkSpace v-if="spec.show_titles && element.title" size="small" />
        </td>
        <td class="form-tuple__td tuple_right" :class="{ has_title: element.title }">
          <FormEditDispatcher
            v-model:data="data[index]"
            :spec="element"
            :backend-validation="elementValidation[index]!"
          />
          <HelpText :help="element.help" />
        </td>
      </tr>
    </tbody>
  </table>

  <template v-if="spec.layout === 'float'">
    <template v-for="(element, index) in spec.elements" :key="index">
      <FormEditDispatcher
        v-model:data="data[index]"
        :spec="element"
        :backend-validation="elementValidation[index]!"
      />
      <HelpText :help="element.help" />
    </template>
  </template>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.valuespec_tuple.horizontal {
  td.form-tuple__td:first-child {
    padding-left: 0;
  }

  td.form-tuple__td {
    padding-left: var(--spacing);
    margin-bottom: var(--spacing-half);
  }
}

.valuespec_tuple.vertical {
  td.form-tuple__td {
    padding-left: 0;
    padding-bottom: var(--spacing-half);
  }

  tr:last-child {
    td.form-tuple__td {
      padding-bottom: 0;
    }
  }
}
</style>
