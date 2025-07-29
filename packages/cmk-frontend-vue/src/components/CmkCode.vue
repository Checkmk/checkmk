<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/tooltip'
import usei18n from '@/lib/i18n'

const { t } = usei18n('cmk-code')

const props = defineProps<{
  title?: string
  code_txt: string
}>()

const TOOLTIP_DISPLAY_DURATION = 8000

const showMessage = ref(false)
const errorMessage = ref('')
let tooltipTimeoutId: ReturnType<typeof setTimeout> | null = null

async function copyToClipboard() {
  if (tooltipTimeoutId !== null) {
    clearTimeout(tooltipTimeoutId)
  }

  try {
    await navigator.clipboard.writeText(props.code_txt)
    errorMessage.value = ''
    showMessage.value = true
    tooltipTimeoutId = setTimeout(() => {
      showMessage.value = false
      tooltipTimeoutId = null
    }, TOOLTIP_DISPLAY_DURATION)
  } catch (err) {
    errorMessage.value = err as string
    showMessage.value = true
    tooltipTimeoutId = setTimeout(() => {
      errorMessage.value = ''
      showMessage.value = false
      tooltipTimeoutId = null
    }, TOOLTIP_DISPLAY_DURATION)
    console.error('Copy failed', err)
  }
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
  <CmkHeading v-if="title" type="h4" class="cmk-code__heading">{{ title }}</CmkHeading>
  <div class="code_wrapper">
    <div class="code_container">
      <pre>
        <code>{{ code_txt.trimStart() }}</code>
      </pre>
    </div>
    <TooltipProvider>
      <Tooltip :open="showMessage" disable-hover-trigger>
        <TooltipTrigger as-child @click="copyToClipboard">
          <CmkIconButton name="copied" size="medium" class="clone_icon" />
        </TooltipTrigger>
        <TooltipContent
          side="top"
          align="center"
          as-child
          @pointer-down-outside="handlePointerDownOutside"
        >
          <div v-if="showMessage" class="tooltip-content" :class="{ error: !!errorMessage }">
            <CmkIcon :name="errorMessage ? 'cross' : 'checkmark'" variant="inline" size="medium" />
            {{
              errorMessage
                ? t('cmk-code-copy-error', 'Copy to clipboard failed with error: ') + errorMessage
                : t('cmk-code-copy-success', 'Copied to clipboard')
            }}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  </div>
</template>

<style scoped>
.cmk-code__heading {
  margin-bottom: 4px;
  color: var(--font-color);
  font-weight: 400;
}

.code_wrapper {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing);
  gap: 8px;

  .code_container {
    font-family: monospace;
    font-size: var(--font-size-normal, 12px);
    font-style: normal;
    font-weight: 400;
    line-height: normal;
    padding: 8px 12px;
    color: var(--font-color);
    border-radius: var(--border-radius);
    border: var(--border-width-1, 1px) solid var(--ux-theme-0);
    background: var(--ux-theme-0);

    pre {
      margin: 0;
      white-space: pre-line;
    }
  }

  .clone_icon {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    border-radius: var(--border-radius);
    border: var(--border-width-1, 1px) solid var(--color-corporate-green-50);
    background: var(--color-corporate-green-50);
    cursor: pointer;
  }
}

.tooltip-content {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  padding: 4px 8px;
  border-radius: var(--border-radius);
  background-color: var(--ux-theme-0);
  color: var(--font-color);
  white-space: nowrap;

  &.error {
    background-color: var(--error-msg-bg-color);
  }
}
</style>
