<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { ref } from 'vue'
import { useFormEditDispatcher } from '@/form/private'

import { immediateWatch } from '@/lib/watch'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { groupNestedValidations, type ValidationMessages } from '@/form/components/utils/validation'
import FormHelp from '../FormHelp.vue'
import { useId } from '@/form/utils'
import HelpText from '@/components/HelpText.vue'
import CmkCheckbox from '@/components/CmkCheckbox.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkHtml from '@/components/CmkHtml.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import FormReadonly from '@/form/components/FormReadonly.vue'
import { rendersRequiredLabelItself } from '@/form/private/requiredValidator'

const DICT_ELEMENT_NO_GROUP = '-ungrouped-'

const dictionaryVariants = cva('', {
  variants: {
    variant: {
      one_column: 'form-dictionary--one_column',
      two_columns: 'form-dictionary--two_columns'
    },
    group_layout: {
      none: '',
      horizontal: 'horizontal_groups',
      vertical: 'vertical_groups'
    }
  },
  defaultVariants: {
    variant: 'one_column',
    group_layout: 'none'
  }
})
type DictionaryVariants = VariantProps<typeof dictionaryVariants>

interface ElementFromProps {
  dict_config: FormSpec.DictionaryElement
  is_active: boolean
}

interface ElementsGroup {
  groupKey: string
  title?: string
  help?: string
  layout: FormSpec.DictionaryGroupLayout
  elems: ElementFromProps[]
}

const props = defineProps<{
  spec: FormSpec.Dictionary
  backendValidation: ValidationMessages
}>()

const variant: DictionaryVariants['variant'] =
  'layout' in props.spec ? props.spec['layout'] : 'one_column'

const data = defineModel<Record<string, unknown>>('data', { required: true })
const elementValidation = ref<Record<string, ValidationMessages>>({})

function getDefaultValue(key: string): unknown {
  const element = props.spec.elements.find((element) => element.name === key)
  if (element === undefined) {
    return undefined
  }
  return element.default_value
}

immediateWatch(
  () => props.spec.additional_static_elements,
  (newAdditionalStaticElements: FormSpec.Dictionary['additional_static_elements'] | undefined) => {
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
    const [, _elementValidation] = groupNestedValidations(props.spec.elements, newValidation)
    elementValidation.value = _elementValidation
  }
)

const getGroupKey = (element: FormSpec.DictionaryElement, index: number): string => {
  if (variant === 'two_columns') {
    return `${DICT_ELEMENT_NO_GROUP}${index}`
  }
  return element.group?.key ?? `${DICT_ELEMENT_NO_GROUP}${index}`
}

const extractGroups = (elements: FormSpec.DictionaryElement[]): ElementsGroup[] => {
  const groups: ElementsGroup[] = []
  elements.forEach((element: FormSpec.DictionaryElement, index: number) => {
    const groupKey = getGroupKey(element, index)
    if (!groups.some((group) => group.groupKey === groupKey)) {
      groups.push({
        groupKey: groupKey,
        title: element.group?.title || '',
        help: element.group?.help || '',
        layout: element.group?.layout || 'horizontal',
        elems: []
      })
    }
  })

  return groups
}

function getElementsInGroupsFromProps(): ElementsGroup[] {
  const groups = extractGroups(props.spec.elements)

  props.spec.elements.forEach((element: FormSpec.DictionaryElement, index: number) => {
    const isActive = element.name in data.value ? true : element.required
    if (isActive && data.value[element.name] === undefined) {
      data.value[element.name] = structuredClone(getDefaultValue(element.name))
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

function toggleElement(key: string) {
  if (key in data.value) {
    delete data.value[key]
  } else {
    data.value[key] = getDefaultValue(key)
  }
}

function indentRequired(
  element: FormSpec.DictionaryElement,
  layout: FormSpec.DictionaryGroupLayout
): boolean {
  return (
    labelRequired(element) &&
    !(element.group && variant === 'one_column' && layout === 'horizontal') &&
    !(
      element.parameter_form.type === 'fixed_value' &&
      !(element.parameter_form as FormSpec.FixedValue).label &&
      !(element.parameter_form as FormSpec.FixedValue).value
    )
  )
}

function labelRequired(element: FormSpec.DictionaryElement): boolean {
  return !(
    element.required &&
    element.parameter_form.title === '' &&
    element.parameter_form.type === 'boolean_choice'
  )
}

const componentId = useId()

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <table
    v-if="props.spec.elements.length > 0"
    class="dictionary"
    :class="dictionaryVariants({ variant })"
  >
    <tbody>
      <tr v-for="group in getElementsInGroupsFromProps()" :key="`${componentId}.${group.groupKey}`">
        <td class="dictleft">
          <div v-if="!!group.title" class="form-dictionary__group-title">{{ group?.title }}</div>
          <FormHelp v-if="group.help" :help="group.help" />
          <div :class="dictionaryVariants({ variant, group_layout: group.layout })">
            <div
              v-for="dict_element in group.elems"
              :key="`${componentId}.${dict_element.dict_config.name}`"
              class="form-dictionary__group_elem"
            >
              <template v-if="labelRequired(dict_element.dict_config)">
                <span
                  v-if="
                    !dict_element.dict_config.required ||
                    dict_element.dict_config.parameter_form.title
                  "
                  class="checkbox"
                >
                  <span v-if="dict_element.dict_config.required">
                    <CmkHtml :html="dict_element.dict_config.parameter_form.title" /><FormRequired
                      v-if="!rendersRequiredLabelItself(dict_element.dict_config.parameter_form)"
                      :spec="dict_element.dict_config.parameter_form"
                      :i18n-required="spec.i18n_base.required"
                      :space="'before'"
                    />
                  </span>
                  <CmkCheckbox
                    v-else
                    v-model="dict_element.is_active"
                    :label="dict_element.dict_config.parameter_form.title"
                    @update:model-value="toggleElement(dict_element.dict_config.name)"
                  />
                  <CmkSpace size="small" />
                  <HelpText :help="dict_element.dict_config.parameter_form.help" />
                </span>
              </template>
              <div
                :aria-label="dict_element.dict_config.parameter_form.title"
                :class="{
                  indent: indentRequired(dict_element.dict_config, group.layout),
                  dictelement: indentRequired(dict_element.dict_config, group.layout),
                  'group-with-more-items': group.elems.length > 1
                }"
              >
                <template v-if="dict_element.is_active">
                  <FormEditDispatcher
                    v-if="!dict_element.dict_config.render_only"
                    v-model:data="data[dict_element.dict_config.name]"
                    :spec="dict_element.dict_config.parameter_form"
                    :backend-validation="elementValidation[dict_element.dict_config.name]!"
                  />
                  <FormReadonly
                    v-else
                    :data="data[dict_element.dict_config.name]"
                    :backend-validation="elementValidation[dict_element.dict_config.name]!"
                    :spec="dict_element.dict_config.parameter_form"
                  ></FormReadonly>
                </template>
              </div>
            </div>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
  <span v-else>{{ spec.no_elements_text }}</span>
</template>

<style scoped>
.form-dictionary__group-title {
  font-weight: bold;
  margin: 1em 0 0.2em 0;
}

span.checkbox {
  display: inline-block;
  margin: 0 var(--spacing-half) var(--spacing-half) 0;

  input + .form-dictionary__label {
    cursor: pointer;
  }
}

/* Variants */
.form-dictionary--two_columns > .form-dictionary__group_elem {
  padding: 8px 0;
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  align-items: start;

  > span.checkbox {
    display: inline-block;
    flex-shrink: 0;
    width: 180px;
    margin: 0;
    padding-top: 0;
    font-weight: bold;
    word-wrap: break-word;
    white-space: normal;
  }

  > .dictelement.indent {
    display: inline-block;
    margin: 0;
    padding-left: 0;
    border-left: none;
    padding-top: 1px;
  }
}
.group-with-more-items {
  border: none;
  margin-left: 0;
  margin-right: 8px;
  padding-left: 0;
}

.form-dictionary--one_column {
  flex-direction: row;
  gap: 0.5em;
  &.horizontal_groups {
    display: flex;
  }
}
</style>
