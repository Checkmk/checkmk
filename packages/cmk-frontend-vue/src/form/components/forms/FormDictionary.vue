<script setup lang="ts">
import { ref } from 'vue'
import FormEdit from '../FormEdit.vue'
import { immediateWatch } from '@/form/components/utils/watch'
import type { Dictionary, DictionaryElement } from '@/form/components/vue_formspec_components'
import {
  groupDictionaryValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'
import FormHelp from '../FormHelp.vue'

const DICT_ELEMENT_NO_GROUP = '-ungrouped-'

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

const data = defineModel('data', { type: Object, required: true })
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

const extractGroups = (elements: DictionaryElement[]): ElementsGroup[] => {
  const groups: ElementsGroup[] = []
  elements.forEach((element: DictionaryElement) => {
    const groupKey = element.group?.key ?? DICT_ELEMENT_NO_GROUP
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

  props.spec.elements.forEach((element: DictionaryElement) => {
    let isActive = element.ident in data.value ? true : element.required
    if (isActive && data.value[element.ident] === undefined) {
      data.value[element.ident] = JSON.parse(JSON.stringify(getDefaultValue(element.ident)))
    }

    const groupIndex = groups.findIndex(
      (group) => group.groupKey === (element.group?.key ?? DICT_ELEMENT_NO_GROUP)
    )
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
  let target = event.target
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
  return !(
    element.required &&
    element.parameter_form.title === '' &&
    element.parameter_form.type === 'boolean_choice'
  )
}
</script>

<template>
  <table class="dictionary">
    <tbody>
      <tr v-for="group in getElementsInGroupsFromProps()" :key="$componentId + group.groupKey">
        <td class="dictleft">
          <div v-if="!!group.title" class="group-title">{{ group?.title }}</div>
          <FormHelp v-if="group.help" :help="group.help" />
          <template
            v-for="dict_element in group.elems"
            :key="$componentId + dict_element.dict_config.ident"
          >
            <template v-if="indentRequired(dict_element.dict_config)">
              <span class="checkbox">
                <input
                  v-if="!dict_element.dict_config.required"
                  :id="$componentId + dict_element.dict_config.ident"
                  v-model="dict_element.is_active"
                  :onclick="
                    (event: MouseEvent) => toggleElement(event, dict_element.dict_config.ident)
                  "
                  type="checkbox"
                />
                <label :for="$componentId + dict_element.dict_config.ident">
                  {{ dict_element.dict_config.parameter_form.title }}
                </label>
              </span>
            </template>
            <div
              :class="{
                indent: indentRequired(dict_element.dict_config),
                dictelement: indentRequired(dict_element.dict_config)
              }"
            >
              <FormEdit
                v-if="dict_element.is_active"
                v-model:data="data[dict_element.dict_config.ident]"
                :spec="dict_element.dict_config.parameter_form"
                :backend-validation="elementValidation[dict_element.dict_config.ident]!"
              />
            </div>
          </template>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.group-title {
  font-weight: bold;
  margin: 1em 0 0.2em 0;
}
</style>
