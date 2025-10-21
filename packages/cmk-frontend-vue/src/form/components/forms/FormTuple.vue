<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref, watch } from 'vue'

import { untranslated } from '@/lib/i18n'
import { capitalizeFirstLetter } from '@/lib/utils'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import {
  type ValidationMessages,
  groupIndexedValidations
} from '@/form/components/utils/validation'
import { useFormEditDispatcher } from '@/form/private'
import FormLabel from '@/form/private/FormLabel.vue'

const props = defineProps<{
  spec: FormSpec.Tuple
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown[]>('data', { required: true })

const validation = ref<Array<string>>([])

type ElementIndex = number
const elementValidation = ref<Record<ElementIndex, ValidationMessages>>({})

watch(
  [() => props.backendValidation],
  ([newBackendValidation]) => {
    setValidation(newBackendValidation)
  },
  { immediate: true }
)

function setValidation(newBackendValidation: ValidationMessages) {
  const [_tupleValidations, _elementValidations] = groupIndexedValidations(
    newBackendValidation,
    props.spec.elements.length
  )
  validation.value = _tupleValidations
  elementValidation.value = _elementValidations
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()

const CLASS_LOOKUP: Record<FormSpec.Tuple['layout'], string> = {
  horizontal_titles_top: 'form-tuple--horizontal-titles-top',
  horizontal: 'form-tuple--horizontal',
  vertical: 'form-tuple--vertical',
  float: 'form-tuple--float'
}
</script>

<template>
  <div class="form-tuple" :class="CLASS_LOOKUP[spec.layout]">
    <div v-for="(element, index) in spec.elements" :key="index" class="form-tuple__item">
      <div v-if="spec.show_titles" class="form-tuple__label">
        <FormLabel v-if="element.title">{{ capitalizeFirstLetter(element.title) }}</FormLabel>
        <CmkSpace
          v-if="spec.show_titles && element.title && spec.layout !== 'horizontal_titles_top'"
          size="small"
        />
        <br v-if="spec.show_titles && element.title && spec.layout === 'horizontal_titles_top'" />
      </div>
      <div class="form-tuple__content">
        <FormEditDispatcher
          v-model:data="data[index]"
          :spec="element"
          :backend-validation="elementValidation[index]!"
        />
        <CmkHelpText :help="untranslated(element.help)" />
      </div>
    </div>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.form-tuple {
  display: flex;
}

/* Horizontal layouts */
.form-tuple.form-tuple--horizontal,
.form-tuple.form-tuple--horizontal-titles-top {
  flex-wrap: wrap;
}

/* Horizontal layout - titles beside content */
.form-tuple.form-tuple--horizontal .form-tuple__item {
  display: flex;
  align-items: flex-start;
}

.form-tuple.form-tuple--vertical .form-tuple__item {
  display: flex;
  margin-bottom: var(--spacing-half);
}

.form-tuple.form-tuple--horizontal .form-tuple__item:not(:first-child),
.form-tuple.form-tuple--horizontal-titles-top .form-tuple__item:not(:first-child) {
  margin-left: var(--spacing);
}

.form-tuple.form-tuple--horizontal .form-tuple__label {
  flex-shrink: 0;
}

/* Vertical layout */
.form-tuple.form-tuple--vertical {
  flex-direction: column;
}

.form-tuple.form-tuple--vertical .form-tuple__item:last-child {
  margin-bottom: 0;
}

.form-tuple.form-tuple--vertical .form-tuple__label {
  flex-shrink: 0;
}

.form-tuple.form-tuple--vertical .form-tuple__content {
  flex: 1;
}

/* Float layout */
.form-tuple.form-tuple--float {
  flex-direction: row;
}

.form-tuple.form-tuple--float .form-tuple__label {
  display: none;
}
</style>
