<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkIconButton from '@/components/CmkIcon.vue'
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
    <div class="icon_container">
      <TooltipProvider>
        <Tooltip :open="showMessage" disable-hover-trigger>
          <TooltipTrigger as-child @click="copyToClipboard">
            <div class="clone_icon_container">
              <CmkIconButton name="copied" variant="inline" size="medium" class="clone_icon" />
            </div>
          </TooltipTrigger>
          <TooltipContent
            side="top"
            align="center"
            as-child
            @pointer-down-outside="handlePointerDownOutside"
          >
            <div v-if="showMessage" class="tooltip-content" :class="{ error: !!errorMessage }">
              <CmkIcon
                :name="errorMessage ? 'cross' : 'checkmark'"
                variant="inline"
                size="medium"
              />
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
  </div>
</template>

<style scoped>
.cmk-code__heading {
  margin-bottom: var(--spacing);
  color: var(--font-color);
}

.code_wrapper {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing);

  .code_container {
    font-family: monospace;
    font-size: var(--font-size-normal, 12px);
    font-style: normal;
    font-weight: 400;
    line-height: normal;
    padding: var(--spacing);
    background: var(--ux-theme-0);
    color: var(--font-color);
    border-radius: var(--spacing-half);

    pre {
      margin: 0;
      white-space: pre-line;
    }
  }

  .icon_container {
    display: flex;
    align-items: center;
    margin-left: var(--spacing);

    .clone_icon_container {
      padding: var(--spacing-half);
      background-color: var(--color-corporate-green-50);
      border-radius: var(--spacing-half);
      cursor: pointer;

      .clone_icon {
        margin-right: 0;
      }
    }
  }
}

.tooltip-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-half);
  padding: var(--spacing-half) var(--spacing);
  border-radius: var(--spacing-half);
  background-color: var(--ux-theme-0);
  color: var(--font-color);
  white-space: nowrap;

  &.error {
    background-color: var(--error-msg-bg-color);
  }
}
</style>
