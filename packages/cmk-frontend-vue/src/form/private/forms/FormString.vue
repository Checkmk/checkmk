<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkDropdownButton from 'cmk-ui-library/components/CmkDropdown/CmkDropdownButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

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

const autoCompleterValue = computed<string | null>({
  get: () => (value.value === '' ? null : value.value),
  set: (v: string | null) => {
    value.value = v ?? ''
  }
})
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
        <CmkInlineValidation :validation="validation"></CmkInlineValidation>
        <div class="form-string--dropdown-container">
          <FormAutocompleter
            :id="componentId"
            v-model="autoCompleterValue"
            :autocompleter="spec.autocompleter"
            :placeholder="untranslated(spec.input_hint ?? '')"
            :label="spec.label || spec.title || ''"
            :start-of-group="true"
          >
            <template #buttons-end>
              <CmkDropdownButton class="form-string__button-clear" group="end" @click="value = ''">
                <CmkIcon name="close" size="small" />
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
  align-items: center;
  padding-top: 0;
  padding-bottom: 1px;
}
</style>
