<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import usei18n from 'cmk-ui-library/lib/i18n'
import { copyToClipboard as copyToClipboardUtil } from 'cmk-ui-library/lib/utils'
import { computed, ref } from 'vue'

const { _t } = usei18n()

const props = defineProps<{
  text: string
  copiedMessage?: string
}>()

const TOOLTIP_DISPLAY_DURATION = 3000
const TOOLTIP_ERROR_DISPLAY_DURATION = 8000

const showMessage = ref(false)
const errorMessage = ref('')
const copiedTooltipText = computed(() => props.copiedMessage ?? _t('Copied to clipboard'))
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
        variant="text"
        :avoid-collisions="true"
        @pointer-down-outside="handlePointerDownOutside"
      >
        <span class="cmk-copy__message">
          <CmkIcon :name="errorMessage ? 'cross' : 'checkmark'" variant="inline" size="medium" />
          {{
            errorMessage
              ? _t('Copy to clipboard failed with error: ') + errorMessage
              : copiedTooltipText
          }}
        </span>
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>

<style scoped>
.cmk-copy__message {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing);
}
</style>
