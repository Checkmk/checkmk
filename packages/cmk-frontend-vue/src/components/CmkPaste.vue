<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

const { _t } = usei18n()

const props = defineProps<{
  inputFirst?: boolean
}>()

const TOOLTIP_DISPLAY_DURATION = 3000
const TOOLTIP_ERROR_DISPLAY_DURATION = 8000

const showMessage = ref(false)
const errorMessage = ref('')
let tooltipTimeoutId: ReturnType<typeof setTimeout> | null = null

const inputWrapper = ref<HTMLElement | null>(null)

const tooltipMessage = computed(() =>
  errorMessage.value
    ? _t('Paste from clipboard failed with error: %{error}', { error: errorMessage.value })
    : _t('Pasted from clipboard')
)

async function pasteFromClipboard() {
  if (tooltipTimeoutId !== null) {
    clearTimeout(tooltipTimeoutId)
  }
  errorMessage.value = ''
  try {
    const text = await navigator.clipboard.readText()
    const input = inputWrapper.value?.querySelector<HTMLInputElement | HTMLTextAreaElement>(
      'input, textarea'
    )
    if (input) {
      input.value = text
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new Event('change', { bubbles: true }))
    } else {
      errorMessage.value = _t('No input field found to paste into')
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'NotAllowedError') {
      // Some browsers (e.g. Firefox) gate clipboard reads behind their own
      // permission prompt; a declined or unavailable prompt lands here.
      errorMessage.value = _t(
        'Clipboard access was blocked. Allow it or paste manually with Ctrl+V.'
      )
    } else {
      errorMessage.value = err instanceof Error ? err.message : _t('Failed to read from clipboard')
    }
    console.error('Paste failed', err)
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

const dismissMessage = () => {
  if (showMessage.value) {
    showMessage.value = false
    if (tooltipTimeoutId !== null) {
      clearTimeout(tooltipTimeoutId)
      tooltipTimeoutId = null
    }
  }
}

onBeforeUnmount(() => {
  if (tooltipTimeoutId !== null) {
    clearTimeout(tooltipTimeoutId)
    tooltipTimeoutId = null
  }
})
</script>

<template>
  <div class="cmk-paste" :class="{ 'cmk-paste--input-first': props.inputFirst }">
    <div class="cmk-paste__trigger">
      <CmkTooltipProvider>
        <CmkTooltip :open="showMessage">
          <CmkTooltipTrigger as-child @click="pasteFromClipboard">
            <slot name="trigger" />
          </CmkTooltipTrigger>
          <CmkTooltipContent
            side="top"
            align="center"
            as-child
            :avoid-collisions="true"
            @pointer-down-outside="dismissMessage"
            @escape-key-down="dismissMessage"
          >
            <div class="cmk-paste__tooltip-content" :class="{ 'cmk-paste__error': !!errorMessage }">
              <CmkIcon
                :name="errorMessage ? 'cross' : 'checkmark'"
                variant="inline"
                size="medium"
              />
              {{ tooltipMessage }}
            </div>
          </CmkTooltipContent>
        </CmkTooltip>
      </CmkTooltipProvider>
    </div>
    <div ref="inputWrapper" class="cmk-paste__input">
      <slot name="input" />
    </div>
  </div>
</template>

<style scoped>
.cmk-paste {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}

.cmk-paste__input {
  flex: 1;
  min-width: 0;
}

.cmk-paste--input-first .cmk-paste__trigger {
  order: 2;
}

.cmk-paste--input-first .cmk-paste__input {
  order: 1;
}

.cmk-paste__tooltip-content {
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

  &.cmk-paste__error {
    background-color: var(--error-msg-bg-color);
  }
}
</style>
