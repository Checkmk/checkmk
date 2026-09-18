<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { ref } from 'vue'

const { text } = defineProps<{
  text?: TranslatedString | undefined
}>()

const open = ref(false)
</script>

<template>
  <slot v-if="text === undefined" />
  <CmkTooltip v-else :open="open" @update:open="open = $event">
    <CmkTooltipTrigger as-child>
      <slot />
    </CmkTooltipTrigger>
    <CmkTooltipContent
      side="right"
      align="center"
      :avoid-collisions="true"
      use-portal
      class="cmk-suggestion-tooltip__popup"
    >
      <span class="cmk-suggestion-tooltip__content">{{ text }}</span>
    </CmkTooltipContent>
  </CmkTooltip>
</template>

<style>
.cmk-suggestion-tooltip__popup {
  z-index: var(--z-index-tooltip-offset);
}
</style>

<style scoped>
.cmk-suggestion-tooltip__content {
  display: inline-block;
  max-width: 320px;
  padding: var(--dimension-3) var(--dimension-4);
  background: var(--default-tooltip-background-color);
  color: var(--default-tooltip-text-color);
  border: 1px solid var(--default-tooltip-text-color);
  border-radius: var(--border-radius);
  font-size: var(--font-size-small);
  line-height: normal;
}
</style>
