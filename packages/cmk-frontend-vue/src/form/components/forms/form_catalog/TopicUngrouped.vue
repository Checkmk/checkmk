<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  TopicElement,
  I18NFormSpecBase
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { groupNestedValidations, type ValidationMessages } from '@/form/components/utils/validation'
import { useId } from '@/form/utils'
import CmkCheckbox from '@/components/CmkCheckbox.vue'
import { onMounted, ref, watch } from 'vue'
import { immediateWatch } from '@/lib/watch'
import { useFormEditDispatcher } from '@/form/private'
import FormRequired from '@/form/private/FormRequired.vue'
import { rendersRequiredLabelItself } from '@/form/private/requiredValidator'

const props = defineProps<{
  elements: TopicElement[]
  backendValidation: ValidationMessages
  i18nBase: I18NFormSpecBase
}>()

const data = defineModel<Record<string, unknown>>('data', { required: true })

const elementValidation = ref<Record<string, ValidationMessages>>({})
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [, nestedValidation] = groupNestedValidations(props.elements, newValidation)
    elementValidation.value = nestedValidation
  }
)

function getDefaultValue(key: string): unknown {
  const element = props.elements.find((element) => element.name === key)
  if (element === undefined) {
    return undefined
  }
  return element.default_value
}

function toggleElement(key: string) {
  if (key in data.value) {
    delete data.value[key]
  } else {
    data.value[key] = getDefaultValue(key)
  }
}

const checkedElements = ref<Record<string, boolean>>({})
onMounted(() => {
  for (const element of props.elements) {
    checkedElements.value[element.name] = element.name in data.value
  }
})

watch(checkedElements, (newCheckedElements) => {
  for (const key in newCheckedElements) {
    if (newCheckedElements[key] && !(key in data.value)) {
      data.value[key] = getDefaultValue(key)
    } else {
      delete data.value[key]
    }
  }
})

const componentId = useId()
// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <tr v-for="element in props.elements" :key="`${componentId}.${element.name}`">
    <td class="title">
      <span class="fixed_content_width">
        <label :class="{ show_pointer: !element.required }">
          <CmkCheckbox
            v-if="!element.required"
            v-model="checkedElements[element.name]!"
            @update:model-value="toggleElement(element.name)"
          />
          <span v-else class="hidden_checkbox_size" />
          {{ element.parameter_form.title
          }}<FormRequired
            v-if="!rendersRequiredLabelItself(element.parameter_form)"
            :spec="element.parameter_form"
            :space="'before'"
          />
        </label>
        <span class="dots">{{ Array(200).join('.') }}</span>
      </span>
    </td>
    <td class="value">
      <FormEditDispatcher
        v-if="element.name in data"
        v-model:data="data[element.name]"
        :spec="element.parameter_form"
        :backend-validation="elementValidation[element.name]!"
      />
    </td>
  </tr>
</template>

<style scoped>
td.title {
  width: 240px;
  min-width: 240px;
  max-width: 240px;
  vertical-align: top;
  span.fixed_content_width {
    width: 230px;
    display: inline-block;
    white-space: nowrap;
    overflow: hidden;
  }

  label {
    &.show_pointer {
      cursor: pointer;
    }
  }
  span.hidden_checkbox_size {
    width: 13px;
    display: inline-block;
  }
}

td.value {
  width: 100%;
  vertical-align: top;
  padding-bottom: 4px;
}
</style>
