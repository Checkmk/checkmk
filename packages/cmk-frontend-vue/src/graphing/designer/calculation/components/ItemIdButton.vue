<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ItemId } from '../../types'
import ItemIdChip from './ItemIdChip.vue'

const {
  id,
  color,
  label,
  blockReason = null
} = defineProps<{
  id: ItemId
  color?: string | undefined
  /** Accessible name of the button. */
  label: TranslatedString
  blockReason?: TranslatedString | null | undefined
}>()

const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <CmkButton
    variant="optional"
    class="graphing-item-id-button"
    :aria-label="label"
    :disabled="blockReason !== null"
    :disabled-reason="blockReason ?? undefined"
    @click="emit('click')"
  >
    <ItemIdChip :id="id" :color="color" />
  </CmkButton>
</template>

<style scoped>
.graphing-item-id-button {
  padding: 0 calc((var(--dimension-10) - var(--dimension-6)) / 2 - var(--dimension-1));
}
</style>
