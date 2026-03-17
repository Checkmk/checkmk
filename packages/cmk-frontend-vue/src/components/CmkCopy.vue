<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'
import { copyToClipboard as copyToClipboardUtil } from '@/lib/utils'

import CmkIcon from '@/components/CmkIcon'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

const { _t } = usei18n()

const props = defineProps<{
  text: string
}>()

const TOOLTIP_DISPLAY_DURATION = 3000
const TOOLTIP_ERROR_DISPLAY_DURATION = 8000

const showMessage = ref(false)
const errorMessage = ref('')
let tooltipTimeoutId: ReturnType<typeof setTimeout> | null = null

async function copyToClipboard() {
  if (tooltipTimeoutId !== null) {
    clearTimeout(tooltipTimeoutId)
  }
  errorMessage.value = ''
  try {
    await copyToClipboardUtil(props.text)
  } catch (err) {
    errorMessage.value = err as string
    console.error('Copy failed', err)
  }
  showMessage.value = true
  tooltipTimeoutId = setTimeout(
    () => {
      showMessage.value = false
      tooltipTimeoutId = null
    },
    errorMessage.value ? TOOLTIP_ERROR_DISPLAY_DURATION : TOOLTIP_DISPLAY_DURATION
  )
}

const handlePointerDownOutside = () => {
  if (showMessage.value) {
    showMessage.value = false
    if (tooltipTimeoutId !== null) {
      clearTimeout(tooltipTimeoutId)
      tooltipTimeoutId = null
    }
  }
}
</script>

<template>
  <CmkTooltipProvider>
    <CmkTooltip :open="showMessage">
      <CmkTooltipTrigger as-child @click="copyToClipboard">
        <slot />
      </CmkTooltipTrigger>
      <CmkTooltipContent
        side="top"
        align="center"
        as-child
        @pointer-down-outside="handlePointerDownOutside"
      >
        <div class="cmk-copy__tooltip-content" :class="{ 'cmk-copy__error': !!errorMessage }">
          <CmkIcon :name="errorMessage ? 'cross' : 'checkmark'" variant="inline" size="medium" />
          {{
            errorMessage
              ? _t('Copy to clipboard failed with error: ') + errorMessage
              : _t('Copied to clipboard')
          }}
        </div>
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>

<style scoped>
.cmk-copy__tooltip-content {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  padding: var(--dimension-3) var(--dimension-4);
  border-radius: var(--border-radius);
  background-color: var(--code-background-color);
  color: var(--font-color);
  white-space: nowrap;
  position: relative;
  z-index: var(--z-index-tooltip-offset);

  &.cmk-copy__error {
    background-color: var(--error-msg-bg-color);
  }
}
</style>
