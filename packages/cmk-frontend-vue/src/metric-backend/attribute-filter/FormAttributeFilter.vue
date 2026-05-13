<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import AttributeFilterPill from './AttributeFilterPill.vue'
import type { AttributeFilterModel, ConnectedCondition } from './types'

const { _t } = usei18n()

defineProps<{
  ariaLabel?: string | undefined
}>()

const model = defineModel<AttributeFilterModel>({ default: () => [] })

function removeCondition(target: ConnectedCondition): void {
  model.value = model.value.filter((c) => c !== target)
}
</script>

<template>
  <div role="group" :aria-label="ariaLabel ?? _t('Attribute filter')">
    <AttributeFilterPill
      v-for="entry in model"
      :key="entry.id"
      :condition="entry"
      removable
      @remove="removeCondition(entry)"
    />
  </div>
</template>
