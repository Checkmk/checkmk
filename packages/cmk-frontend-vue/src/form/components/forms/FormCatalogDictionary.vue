<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DictionaryElement } from '@/form/components/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'
import { immediateWatch } from '@/form/components/utils/watch'
import {
  groupDictionaryValidations,
  requiresSomeInput,
  type ValidationMessages
} from '@/form/components/utils/validation'
import { ref } from 'vue'
import HelpText from '@/components/HelpText.vue'
import FormHelp from '@/form/components/FormHelp.vue'
import { useId } from '@/form/utils'
import { cva, type VariantProps } from 'class-variance-authority'

const props = defineProps<{
  elements: Array<DictionaryElement>
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, unknown>>({ required: true })

// immediateWatch(
//   () => props.elements,
//   (newValue) => {
//     newValue.forEach((element) => {
//       if (!(element.name in data.value)) {
//         data.value[element.name] = element.default_value
//       }
//     })
//   }
// )

const elementValidation = ref<Record<string, ValidationMessages>>({})
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [, _elementValidation] = groupDictionaryValidations(props.elements, newValidation)
    elementValidation.value = _elementValidation
  }
)

function isRequired(element: DictionaryElement): boolean {
  return requiresSomeInput(element.parameter_form.validators)
}

////////////////////////////////////////////////////////
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

const DICT_ELEMENT_NO_GROUP = '-ungrouped-'
const getGroupKey = (element: DictionaryElement, index: number): string => {
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

function getDefaultValue(key: string): unknown {
  const element = props.elements.find((element) => element.name === key)
  if (element === undefined) {
    return undefined
  }
  return element.default_value
}

function getElementsInGroupsFromProps(): ElementsGroup[] {
  const groups = extractGroups(props.elements)

  props.elements.forEach((element: DictionaryElement, index: number) => {
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

function labelRequired(element: DictionaryElement): boolean {
  return !(
    element.required &&
    element.parameter_form.title === '' &&
    element.parameter_form.type === 'boolean_choice'
  )
}

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

const variant: DictionaryVariants['variant'] = 'two_columns'

function indentRequired(element: DictionaryElement): boolean {
  return labelRequired(element) && !(element.group && variant === 'one_column')
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

const componentId = useId()
</script>

<template>
  <template v-if="getElementsInGroupsFromProps().length === 1">
    <tr v-for="element in elements" :key="element.name">
      <td class="legend">
        <div class="title">
          {{ element.parameter_form.title }}
          <HelpText :help="element.parameter_form.help" />
          <span
            class="dots"
            :class="{
              required: isRequired(element)
            }"
          >
            {{ Array(200).join('.') }}</span
          >
        </div>
      </td>
      <td class="content">
        <FormEdit
          v-model:data="data[element.name]!"
          :backend-validation="elementValidation[element.name]!"
          :spec="element.parameter_form"
        />
      </td>
    </tr>
  </template>

  <template v-if="getElementsInGroupsFromProps().length > 1">
    <template
      v-for="group in getElementsInGroupsFromProps()"
      :key="`${componentId}.${group.groupKey}`"
    >
      <tr>
        <td class="legend">
          <div v-if="!!group.title" class="form-dictionary__group-title title">
            {{ group?.title }}
            <span class="dots">
              {{ Array(200).join('.') }}
            </span>
          </div>
        </td>
        <td />
      </tr>
      <FormHelp v-if="group.help" :help="group.help" />
      <template
        v-for="dict_element in group.elems"
        :key="`${componentId}.${dict_element.dict_config.name}`"
      >
        <tr>
          <td class="legend"></td>
          <td class="dictleft dictkey">
            <div :class="dictionaryVariants({ variant })">
              <div class="form-dictionary__group_elem">
                <template v-if="labelRequired(dict_element.dict_config)">
                  <table>
                    <tbody>
                      <tr>
                        <td class="checkbox">
                          <input
                            v-if="!dict_element.dict_config.required"
                            :id="`${componentId}.${dict_element.dict_config.name}`"
                            v-model="dict_element.is_active"
                            class="checkbox"
                            :onclick="
                              (event: MouseEvent) =>
                                toggleElement(event, dict_element.dict_config.name)
                            "
                            type="checkbox"
                          />
                          <label :for="`${componentId}.${dict_element.dict_config.name}`" />
                        </td>
                        <td>
                          <label
                            v-if="dict_element.dict_config.parameter_form.title"
                            :for="`${componentId}.${dict_element.dict_config.name}`"
                          >
                            {{ dict_element.dict_config.parameter_form.title }}
                          </label>
                          <HelpText :help="dict_element.dict_config.parameter_form.help" />
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </template>
              </div>
            </div>
            <div
              :class="{
                indent: indentRequired(dict_element.dict_config),
                dictelement: indentRequired(dict_element.dict_config),
                'group-with-more-items': group.elems.length > 1
              }"
            >
              <FormEdit
                v-if="dict_element.is_active"
                v-model:data="data[dict_element.dict_config.name]"
                :spec="dict_element.dict_config.parameter_form"
                :backend-validation="elementValidation[dict_element.dict_config.name]!"
                :aria-label="dict_element.dict_config.parameter_form.title"
              />
            </div>
          </td>
        </tr>
      </template>
    </template>
  </template>
</template>

<style scoped>
td.legend {
  max-width: 200px !important;
}
td.dictkey {
  padding-left: 20px !important;
}
td.checkbox {
  vertical-align: top;
  width: 12.5px;
}
</style>
