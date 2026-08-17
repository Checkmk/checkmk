<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import type { DraftConstantItem } from '../../drafts'
import SourceFormField from './SourceFormField.vue'

const { item, store, valueErrors } = defineProps<{
  item: DraftConstantItem
  store: GraphItemsStore
  valueErrors: TranslatedString[]
}>()

const { _t } = usei18n()

function onValueChange(value: unknown): void {
  const parsed = parseFloat(String(value))
  store.replace({ ...item, value: Number.isFinite(parsed) ? parsed : null })
}
</script>

<template>
  <SourceFormField
    v-slot="{ controlId, describedBy }"
    class="graphing-constant-line-form"
    :label="_t('Constant at')"
    label-variant="name"
    required
    :errors="valueErrors"
  >
    <CmkInput
      :id="controlId"
      :model-value="item.value ?? undefined"
      type="number"
      :placeholder="_t('Value')"
      :external-errors="valueErrors"
      hide-validation-message
      :described-by="describedBy"
      @update:model-value="onValueChange"
    />
  </SourceFormField>
</template>

<style scoped>
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-constant-line-form :deep(input.cmk-input--number) {
  width: 66px;
}
</style>
