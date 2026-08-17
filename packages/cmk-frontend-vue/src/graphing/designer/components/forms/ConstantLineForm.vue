<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import type { DraftConstantItem } from '../../drafts'

const { item, store, valueErrors } = defineProps<{
  item: DraftConstantItem
  store: GraphItemsStore
  valueErrors: TranslatedString[]
}>()

const { _t } = usei18n()

const valueInputId = useId()

function onValueChange(value: unknown): void {
  const parsed = parseFloat(String(value))
  store.replace({ ...item, value: Number.isFinite(parsed) ? parsed : null })
}
</script>

<template>
  <div class="graphing-constant-line-form">
    <div class="graphing-constant-line-form__field">
      <CmkLabel variant="subtitle" :for="valueInputId">{{ _t('Constant at') }}</CmkLabel>
      <CmkInput
        :id="valueInputId"
        :model-value="item.value ?? undefined"
        type="number"
        :placeholder="_t('Value')"
        :external-errors="valueErrors"
        @update:model-value="onValueChange"
      />
    </div>
  </div>
</template>

<style scoped>
.graphing-constant-line-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.graphing-constant-line-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-constant-line-form__field :deep(input.cmk-input--number) {
  width: 66px;
}
</style>
