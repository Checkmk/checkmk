<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import {
  groupIndexedValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'
import { ref, watch } from 'vue'
import FormValidation from '@/form/components/FormValidation.vue'
import HelpText from '@/components/HelpText.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import { capitalizeFirstLetter } from '@/lib/utils'
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
</script>

<template>
  <div class="form-tuple" :class="spec.layout">
    <div v-for="(element, index) in spec.elements" :key="index" class="form-tuple_item">
      <div v-if="spec.show_titles" class="form-tuple_label">
        <FormLabel v-if="element.title">{{ capitalizeFirstLetter(element.title) }}</FormLabel>
        <CmkSpace
          v-if="spec.show_titles && element.title && spec.layout !== 'horizontal_titles_top'"
          size="small"
        />
        <br v-if="spec.show_titles && element.title && spec.layout === 'horizontal_titles_top'" />
      </div>
      <div class="form-tuple_content">
        <FormEditDispatcher
          v-model:data="data[index]"
          :spec="element"
          :backend-validation="elementValidation[index]!"
        />
        <HelpText :help="element.help" />
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
.form-tuple.horizontal,
.form-tuple.horizontal_titles_top {
  flex-wrap: wrap;
}

.form-tuple.horizontal .form-tuple_item:not(:first-child),
.form-tuple.horizontal_titles_top .form-tuple_item:not(:first-child) {
  margin-left: var(--spacing);
}

/* Horizontal layout - titles beside content */
.form-tuple.horizontal .form-tuple_item {
  display: flex;
  align-items: flex-start;
}

.form-tuple.horizontal .form-tuple_label {
  flex-shrink: 0;
}

/* Vertical layout */
.form-tuple.vertical {
  flex-direction: column;
}

.form-tuple.vertical .form-tuple_item {
  display: flex;
  margin-bottom: var(--spacing-half);
}

.form-tuple.vertical .form-tuple_item:last-child {
  margin-bottom: 0;
}

.form-tuple.vertical .form-tuple_label {
  flex-shrink: 0;
}

.form-tuple.vertical .form-tuple_content {
  flex: 1;
}

/* Float layout */
.form-tuple.float {
  flex-direction: row;
}

.form-tuple.float .form-tuple_label {
  display: none;
}
</style>
