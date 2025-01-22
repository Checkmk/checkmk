/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type { ValidationMessages } from '@/form'
import { groupIndexedValidations, validateValue } from '@/form/components/utils/validation'
import type { Ref } from 'vue'
import type { Validator } from 'cmk-shared-typing/typescript/vue_formspec_components'

export default function formListActions(
  props: {
    spec: { element_default_value: unknown; validators: Validator[] }
    backendValidation: ValidationMessages
  },
  data: Ref<unknown[]>,
  validation: Ref<Array<string>>,
  elementValidation: Ref<Array<ValidationMessages>>
): {
  initialize: (newBackendData: unknown[]) => void
  deleteElement: (index: number) => boolean
  addElement: (index: number) => boolean
  updateElementData: (newValue: unknown, index: number) => void
  setValidation: (newBackendValidation: ValidationMessages) => void
} {
  function initialize(newBackendData: unknown[]) {
    validation.value.splice(0)
    elementValidation.value.splice(0)
    newBackendData.forEach(() => {
      elementValidation.value.push([] as ValidationMessages)
    })
  }

  function deleteElement(index: number) {
    data.value.splice(index, 1)
    elementValidation.value.splice(index, 1)
    _validateList()
    return true
  }

  function addElement(index: number) {
    data.value[index] = JSON.parse(JSON.stringify(props.spec.element_default_value))
    elementValidation.value[index] = []
    _validateList()
    return true
  }

  function updateElementData(newValue: unknown, index: number) {
    data.value[index] = newValue
  }

  function setValidation(newBackendValidation: ValidationMessages) {
    const [_listValidations, _elementValidations] = groupIndexedValidations(
      newBackendValidation,
      data.value.length
    )
    validation.value = _listValidations
    Object.entries(_elementValidations).forEach(([i, value]) => {
      elementValidation.value[i as unknown as number] = value
    })
  }

  function _validateList() {
    validation.value = []
    validateValue(data.value, props.spec.validators!).forEach((error) => {
      validation.value.push(error)
    })
  }
  return {
    initialize,
    deleteElement,
    addElement,
    updateElementData,
    setValidation
  }
}
