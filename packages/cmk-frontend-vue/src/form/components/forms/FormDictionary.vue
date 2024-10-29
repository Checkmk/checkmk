<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { ref } from 'vue'

import FormEdit from '../FormEdit.vue'
import { immediateWatch } from '@/form/components/utils/watch'
import type { Dictionary, DictionaryElement } from '@/form/components/vue_formspec_components'
import {
  groupDictionaryValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'
import FormHelp from '../FormHelp.vue'
import { useId } from '@/form/utils'
import HelpText from '@/components/HelpText.vue'

const DICT_ELEMENT_NO_GROUP = '-ungrouped-'

const dictionaryVariants = cva('', {
  variants: {
    variant: {
      one_column: 'form-dictionary--one_column',
      two_columns: 'form-dictionary--two_columns'
    }
  },
  defaultVariants: {
    variant: 'one_column'
  }
})
type DictionaryVariants = VariantProps<typeof dictionaryVariants>

interface ElementFromProps {
  dict_config: DictionaryElement
  is_active: boolean
}

interface ElementsGroup {
  groupKey: string
  title?: string
  help?: string
  elems: ElementFromProps[]
}

const props = defineProps<{
  spec: Dictionary
  backendValidation: ValidationMessages
}>()

const variant: DictionaryVariants['variant'] =
  'layout' in props.spec ? props.spec['layout'] : 'one_column'

const data = defineModel<Record<string, unknown>>('data', { required: true })
const elementValidation = ref<Record<string, ValidationMessages>>({})

function getDefaultValue(key: string): unknown {
  const element = props.spec.elements.find((element) => element.ident === key)
  if (element === undefined) {
    return undefined
  }
  return element.default_value
}

immediateWatch(
  () => props.spec.additional_static_elements,
  (newAdditionalStaticElements: Dictionary['additional_static_elements'] | undefined) => {
    if (newAdditionalStaticElements) {
      for (const [key, value] of Object.entries(newAdditionalStaticElements)) {
        data.value[key] = value
      }
    }
  }
)

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [, _elementValidation] = groupDictionaryValidations(props.spec.elements, newValidation)
    elementValidation.value = _elementValidation
  }
)

const getGroupKey = (element: DictionaryElement, index: number): string => {
  if (variant === 'two_columns') {
    return `${DICT_ELEMENT_NO_GROUP}${index}`
  }
  return element.group?.key ?? `${DICT_ELEMENT_NO_GROUP}${index}`
}

const extractGroups = (elements: DictionaryElement[]): ElementsGroup[] => {
  const groups: ElementsGroup[] = []
  elements.forEach((element: DictionaryElement, index: number) => {
    const groupKey = getGroupKey(element, index)
    if (!groups.some((group) => group.groupKey === groupKey)) {
      groups.push({
        groupKey: groupKey,
        title: element.group?.title || '',
        help: element.group?.help || '',
        elems: []
      })
    }
  })

  return groups
}

function getElementsInGroupsFromProps(): ElementsGroup[] {
  const groups = extractGroups(props.spec.elements)

  props.spec.elements.forEach((element: DictionaryElement, index: number) => {
    const isActive = element.ident in data.value ? true : element.required
    if (isActive && data.value[element.ident] === undefined) {
      data.value[element.ident] = structuredClone(getDefaultValue(element.ident))
    }

    const groupIndex = groups.findIndex((group) => group.groupKey === getGroupKey(element, index))
    if (groupIndex === -1) {
      throw new Error('Group not found')
    }
    if (groups[groupIndex]) {
      groups[groupIndex]!.elems.push({
        dict_config: element,
        is_active: isActive
      })
    }
  })
  return groups
}

function toggleElement(event: MouseEvent, key: string) {
  const target = event.target
  if (!target) {
    return
  }
  if (key in data.value) {
    delete data.value[key]
  } else {
    data.value[key] = getDefaultValue(key)
  }
}

function indentRequired(element: DictionaryElement): boolean {
  return labelRequired(element) && !(element.group && variant === 'one_column')
}

function labelRequired(element: DictionaryElement): boolean {
  return !(
    element.required &&
    element.parameter_form.title === '' &&
    element.parameter_form.type === 'boolean_choice'
  )
}

const componentId = useId()
</script>

<template>
  <table class="dictionary" :class="dictionaryVariants({ variant })">
    <tbody>
      <tr v-for="group in getElementsInGroupsFromProps()" :key="`${componentId}.${group.groupKey}`">
        <td class="dictleft">
          <div v-if="!!group.title" class="form-dictionary__group-title">{{ group?.title }}</div>
          <FormHelp v-if="group.help" :help="group.help" />
          <div :class="dictionaryVariants({ variant })">
            <div
              v-for="dict_element in group.elems"
              :key="`${componentId}.${dict_element.dict_config.ident}`"
              class="form-dictionary__group_elem"
            >
              <template v-if="labelRequired(dict_element.dict_config)">
                <span class="checkbox">
                  <input
                    v-if="!dict_element.dict_config.required"
                    :id="`${componentId}.${dict_element.dict_config.ident}`"
                    v-model="dict_element.is_active"
                    :onclick="
                      (event: MouseEvent) => toggleElement(event, dict_element.dict_config.ident)
                    "
                    type="checkbox"
                  />
                  <label
                    v-if="dict_element.dict_config.parameter_form.title"
                    :for="`${componentId}.${dict_element.dict_config.ident}`"
                  >
                    {{ dict_element.dict_config.parameter_form.title }}
                  </label>
                  <HelpText :help="dict_element.dict_config.parameter_form.help" />
                </span>
              </template>
              <div
                :class="{
                  indent: indentRequired(dict_element.dict_config),
                  dictelement: indentRequired(dict_element.dict_config),
                  'group-with-more-items': group.elems.length > 1
                }"
              >
                <FormEdit
                  v-if="dict_element.is_active"
                  v-model:data="data[dict_element.dict_config.ident]"
                  :spec="dict_element.dict_config.parameter_form"
                  :backend-validation="elementValidation[dict_element.dict_config.ident]!"
                  :aria-label="dict_element.dict_config.parameter_form.title"
                />
              </div>
            </div>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.form-dictionary__group-title {
  font-weight: bold;
  margin: 1em 0 0.2em 0;
}

span.checkbox {
  margin-bottom: 5px;
  margin-right: 5px;
}

span.checkbox input + label {
  cursor: pointer;
}

/* Variants */
.form-dictionary--two_columns > .form-dictionary__group_elem {
  padding: 8px 0;
  display: flex;
  flex-direction: row;
  justify-content: flex-start;

  > span.checkbox {
    display: inline-block;
    width: 160px;
    margin: 0;
    padding-top: 3px;
    font-weight: bold;
    word-wrap: break-word;
    white-space: normal;
  }

  > .dictelement.indent {
    display: inline-block;
    margin: 0;
    padding-left: 0;
    border-left: none;
  }
}
.group-with-more-items {
  border: none;
  margin-left: 0;
  margin-right: 8px;
  padding-left: 0;
}

.form-dictionary--one_column {
  display: flex;
  flex-direction: row;
  gap: 0.5em;
}
</style>
