<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SingleChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'

import { untranslated } from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkDropdown from '@/components/CmkDropdown'
import CmkSpace from '@/components/CmkSpace.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import FormLabel from '@/form/private/FormLabel.vue'
import { type ValidationMessages, useValidation } from '@/form/private/validation'

const props = defineProps<{
  spec: SingleChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<string | null>('data', { required: true })
const [validation, value] = useValidation<string | null>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <div class="form-single-choice">
    <div class="form-single-choice__layout">
      <div class="form-single-choice__label-column">
        <div class="form-single-choice__label-spacer"></div>
        <FormLabel v-if="$props.spec.label" :for="componentId"
          >{{ spec.label }}<CmkSpace size="small"
        /></FormLabel>
      </div>
      <div class="form-single-choice__input-column">
        <FormValidation :validation="validation"></FormValidation>
        <div v-if="props.spec.elements.length === 0">
          {{ untranslated(props.spec.no_elements_text || '') }}
        </div>
        <CmkDropdown
          v-else
          v-model:selected-option="value"
          :options="{
            type: props.spec.elements.length > 5 ? 'filtered' : 'fixed',
            suggestions: props.spec.elements.map((element) => ({
              name: element.name,
              title: untranslated(element.title)
            }))
          }"
          :input-hint="untranslated(props.spec.input_hint || '')"
          :disabled="spec.frozen"
          :component-id="componentId"
          :no-results-hint="untranslated(props.spec.no_elements_text || '')"
          :label="untranslated(props.spec.label || props.spec.title)"
          :form-validation="validation.length > 0"
          required
        />
      </div>
    </div>
  </div>
</template>
<style scoped>
.form-single-choice__layout {
  display: flex;
}

.form-single-choice__label-column {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.form-single-choice__label-spacer {
  flex-grow: 1;
}

.form-single-choice__input-column {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
