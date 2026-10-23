<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Components, TopicElement } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { onMounted, ref, watch } from 'vue'

import FormEditDispatcher from '@/form/private/FormEditDispatcher/FormEditDispatcher.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import { helpAtTitle } from '@/form/private/rendersHelpItself'
import { rendersRequiredLabelItself } from '@/form/private/requiredValidator'
import { type ValidationMessages, groupNestedValidations } from '@/form/private/validation'

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
</script>

<template>
  <tr
    v-for="element in props.elements"
    :key="`${componentId}.${element.name}`"
    class="form-topic-ungrouped__root"
  >
    <td class="form-topic-ungrouped__title">
      <span class="form-topic-ungrouped__fixed-content-width">
        <CmkCheckbox
          v-if="!element.required"
          v-model="checkedElements[element.name]!"
          class="form-topic-ungrouped__checkbox"
          :help="untranslated(helpAtTitle(element.parameter_form, !!checkedElements[element.name]))"
          :label="untranslated(element.parameter_form.title)"
          label-position="left"
          dots
          @update:model-value="toggleElement(element.name)"
        />
        <CmkLabel
          v-else-if="element.parameter_form.title.length > 0"
          :help="untranslated(helpAtTitle(element.parameter_form))"
          dots
        >
          {{ element.parameter_form.title
          }}<FormRequired
            v-if="!rendersRequiredLabelItself(element.parameter_form)"
            :spec="element.parameter_form"
            :space="'before'"
          />
        </CmkLabel>
      </span>
    </td>
    <td class="form-topic-ungrouped__value">
      <FormEditDispatcher
        v-if="element.name in data"
        v-model:data="data[element.name]"
        :spec="element.parameter_form as Components"
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
}

.form-topic-ungrouped__title {
  width: 240px;
  min-width: 240px;
  max-width: 240px;
  padding: 5px 2px;
  color: var(--font-color);
  display: table-cell;
  letter-spacing: 1px;
}

.form-topic-ungrouped__value {
  width: 100%;
  padding: 5px 0 4px;
  white-space: nowrap;
}

.form-topic-ungrouped__fixed-content-width {
  width: 230px;
  display: inline-block;
  overflow: hidden;
}

.form-topic-ungrouped__checkbox {
  width: 100%;
}

.form-topic-ungrouped__root:nth-child(1) > td {
  padding-top: 5px;
}
</style>
