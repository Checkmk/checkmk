<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { X } from 'lucide-vue-next'

import { untranslated } from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkDropdownButton from '@/components/CmkDropdown/CmkDropdownButton.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'
import FormLabel from '@/form/private/FormLabel.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import { type ValidationMessages, useValidation } from '@/form/private/validation'

defineOptions({
  inheritAttrs: false
})

const props = defineProps<{
  spec: FormSpec.String
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })
const [validation, value] = useValidation<string>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <div class="form-string__validation-wrapper">
    <div class="form-string__label">
      <template v-if="props.spec.label">
        <FormLabel :for="componentId">{{ props.spec.label }}<CmkSpace size="small" /> </FormLabel>
        <FormRequired :spec="props.spec" :space="'after'" />
      </template>
    </div>
    <template v-if="spec.autocompleter">
      <div class="form-string__autocomplete-wrapper">
        <FormValidation :validation="validation"></FormValidation>
        <div class="form-string--dropdown-container">
          <FormAutocompleter
            :id="componentId"
            v-model="value"
            :autocompleter="spec.autocompleter"
            :placeholder="untranslated(spec.input_hint ?? '')"
            :label="spec.label || ''"
            :start-of-group="true"
          >
            <template #buttons-end>
              <CmkDropdownButton class="form-string__button-clear" group="end" @click="value = ''">
                <X class="form-string__button-clear-x" />
              </CmkDropdownButton>
            </template>
          </FormAutocompleter>
        </div>
      </div>
    </template>
    <CmkInput
      v-else
      :id="componentId"
      v-model="value"
      :type="'text'"
      :placeholder="untranslated(spec.input_hint || '')"
      :aria-label="untranslated(spec.label || spec.title || '')"
      :field-size="props.spec.field_size"
      :external-errors="validation"
    />
  </div>
</template>

<style scoped>
.form-string__validation-wrapper {
  display: flex;
  flex-direction: row;
}

.form-string__label {
  display: flex;
  align-items: flex-end;
}

.form-string__autocomplete-wrapper {
  display: flex;
  flex-direction: column;
}

.form-string__button-clear {
  vertical-align: bottom;
  margin-left: 1px;
}

.form-string__button-clear-x {
  width: 13px;
  height: 14px;
}
</style>
