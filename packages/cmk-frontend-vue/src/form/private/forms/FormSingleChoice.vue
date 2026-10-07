<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SingleChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'

import FormLabel from '@/form/private/FormLabel.vue'
import FormRequired from '@/form/private/FormRequired.vue'
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
          >{{ spec.label }}<FormRequired :spec="props.spec" :space="'before'" /><CmkSpace
            size="small"
        /></FormLabel>
      </div>
      <div class="form-single-choice__input-column">
        <CmkInlineValidation :validation="validation"></CmkInlineValidation>
        <div v-if="props.spec.elements.length === 0">
          {{ untranslated(props.spec.no_elements_text || '') }}
        </div>
        <CmkDropdown
          v-else
          v-model="value"
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
          :required="!props.spec.label && !props.spec.title"
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
