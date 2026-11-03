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
      variant="content"
      :avoid-collisions="true"
      use-portal
    >
      <span class="cmk-suggestion-tooltip__content">{{ text }}</span>
    </CmkTooltipContent>
  </CmkTooltip>
</template>

<style scoped>
.cmk-suggestion-tooltip__content {
  display: inline-block;
  max-width: 320px;
}
</style>
