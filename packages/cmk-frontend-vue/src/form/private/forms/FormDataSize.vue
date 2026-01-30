<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DataSize } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import { untranslated } from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkDropdown from '@/components/CmkDropdown'
import CmkSpace from '@/components/CmkSpace.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FormLabel from '@/form/private/FormLabel.vue'
import { type ValidationMessages, useValidation } from '@/form/private/validation'

const props = defineProps<{
  spec: DataSize
  backendValidation: ValidationMessages
}>()

const data = defineModel<[string, string]>('data', { required: true })

const [validation, value] = useValidation<[string, string]>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const value0Number = computed({
  get() {
    const n = Number(value.value[0])
    return isNaN(n) ? undefined : n
  },
  set(val: number | undefined) {
    value.value[0] = val === undefined || val === null ? '' : String(val)
  }
})

const componentId = useId()

const magnitudeOptions = computed(() => {
  return props.spec.displayed_magnitudes.map((element: string) => {
    return {
      name: element,
      title: untranslated(element)
    }
  })
})
</script>

<template>
  <div class="form-data-size__layout">
    <div class="form-data-size__label-column">
      <FormLabel :for="componentId"> {{ props.spec.label }}<CmkSpace size="small" /> </FormLabel>
    </div>
    <CmkSpace size="small" />
    <div class="form-data-size__validation-wrapper">
      <FormValidation :validation="validation" />
      <div class="form-single-choice__input-column--inner">
        <CmkInput
          :id="componentId"
          v-model="value0Number"
          :placeholder="spec.input_hint || ''"
          :class="{ 'form-data-size__error': validation.length > 0 }"
          step="any"
          type="number"
          :inline="true"
        />
        <CmkSpace size="small" />
        <CmkDropdown
          v-model:selected-option="value[1]"
          :options="{ type: 'fixed', suggestions: magnitudeOptions }"
          :label="untranslated(spec.i18n.choose_unit)"
          :form-validation="validation.length > 0"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.form-data-size__error {
  border: 1px solid var(--inline-error-border-color);
}

.form-data-size__layout {
  display: flex;
}

.form-data-size__label-column {
  flex-shrink: 0;
  display: flex;
  align-items: end;
}

.form-data-size__validation-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.form-data-size__input-column--inner {
  display: flex;
  align-items: center;
}
</style>
