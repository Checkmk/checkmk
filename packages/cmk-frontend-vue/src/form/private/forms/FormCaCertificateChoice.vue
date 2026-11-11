<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  CaCertificateChoice,
  ValueSummary
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'

import FormReadonly from '@/form/FormReadonly.vue'
import type { ValidationMessages } from '@/form/private/validation'

const props = defineProps<{
  spec: CaCertificateChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown[]>('data', { required: true })

function summarySpec(element: ValueSummary): CaCertificateChoice {
  return { ...props.spec, elements: [element] }
}

function choose(certificate: unknown, isChosen: boolean) {
  data.value = props.spec.elements
    .map((element) => element.value)
    .filter((value) => (value === certificate ? isChosen : data.value.includes(value)))
}
</script>

<template>
  <div role="group" :aria-label="spec.title">
    <CmkCheckbox
      v-for="(element, index) in spec.elements"
      :key="index"
      :model-value="data.includes(element.value)"
      :aria-label="untranslated(spec.chosen_label)"
      @update:model-value="(isChosen: boolean) => choose(element.value, isChosen)"
    >
      <FormReadonly :spec="summarySpec(element)" :data="data" :backend-validation="[]" />
    </CmkCheckbox>
  </div>
</template>
