/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref } from 'vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

const DICT_ELEMENT_NO_GROUP = '-ungrouped-'

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

const getGroupKey = (element: FormSpec.DictionaryElement, index: number): string => {
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

export function getDefaultValue(elements: FormSpec.Dictionary['elements'], key: string): unknown {
  const element = elements.find((element) => element.name === key)
  if (element === undefined) {
    return undefined
  }
  return JSON.parse(JSON.stringify(element.default_value))
}

export function getElementsInGroupsFromProps(
  elements: FormSpec.Dictionary['elements'],
  data: Ref<Record<string, unknown>>
): ElementsGroup[] {
  const groups = extractGroups(elements)

  elements.forEach((element: FormSpec.DictionaryElement, index: number) => {
    const isActive = element.name in data.value ? true : element.required
    if (isActive && data.value[element.name] === undefined) {
      data.value[element.name] = structuredClone(getDefaultValue(elements, element.name))
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

export function titleRequired(element: FormSpec.DictionaryElement): boolean {
  return (
    (!element.required || element.parameter_form.title !== '') &&
    !(
      element.required &&
      element.parameter_form.title === '' &&
      element.parameter_form.type === 'boolean_choice'
    )
  )
}

export function toggleElement(
  data: Record<string, unknown>,
  elements: FormSpec.Dictionary['elements'],
  key: string
) {
  if (key in data) {
    delete data[key]
  } else {
    data[key] = getDefaultValue(elements, key)
  }
}
