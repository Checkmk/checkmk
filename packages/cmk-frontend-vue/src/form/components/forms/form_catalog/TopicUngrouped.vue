<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TopicElement } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { onMounted, ref, watch } from 'vue'

import { immediateWatch } from '@/lib/watch'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import { type ValidationMessages, groupNestedValidations } from '@/form/components/utils/validation'
import { useFormEditDispatcher } from '@/form/private'
import FormRequired from '@/form/private/FormRequired.vue'
import { rendersRequiredLabelItself } from '@/form/private/requiredValidator'
import { useId } from '@/form/utils'

const props = defineProps<{
  elements: TopicElement[]
  backendValidation: ValidationMessages
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
  <tr
    v-for="element in props.elements"
    :key="`${componentId}.${element.name}`"
    class="form-topic-ungrouped__root"
  >
    <td class="form-topic-ungrouped__title">
      <span class="form-topic-ungrouped__fixed-content-width">
        <label :class="{ 'form-topic-ungrouped__show-pointer': !element.required }">
          <CmkCheckbox
            v-if="!element.required"
            v-model="checkedElements[element.name]!"
            @update:model-value="toggleElement(element.name)"
          />
          <span v-else class="form-topic-ungrouped__hidden-checkbox-size" />
          {{ element.parameter_form.title
          }}<FormRequired
            v-if="!rendersRequiredLabelItself(element.parameter_form)"
            :spec="element.parameter_form"
            :space="'before'"
          />
        </label>
        <span class="form-topic-ungrouped__dots">{{ Array(200).join('.') }}</span>
      </span>
    </td>
    <td class="form-topic-ungrouped__value">
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
.form-topic-ungrouped__title,
.form-topic-ungrouped__value {
  vertical-align: top;
  font-weight: 400;
  empty-cells: show;
  white-space: nowrap;
}

.form-topic-ungrouped__title {
  width: 240px;
  min-width: 240px;
  max-width: 240px;
  padding: 5px 2px;
  color: #333;
  display: table-cell;
  letter-spacing: 1px;
}

.form-topic-ungrouped__dots {
  margin-left: 5px;
  overflow: hidden;
  color: rgb(51 51 51 / 80%);
}

.form-topic-ungrouped__hidden-checkbox-size {
  width: 13px;
  display: inline-block;
}

.form-topic-ungrouped__show-pointer {
  cursor: pointer;
}

.form-topic-ungrouped__value {
  width: 100%;
  padding: 5px 0 4px;
}

.form-topic-ungrouped__fixed-content-width {
  width: 230px;
  display: inline-block;
  white-space: nowrap;
  overflow: hidden;
}
</style>
