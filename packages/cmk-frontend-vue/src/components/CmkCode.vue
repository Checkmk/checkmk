<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, computed } from 'vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkButton from '@/components/CmkButton.vue'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/tooltip'
import usei18n from '@/lib/i18n'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

const { t } = usei18n('cmk-code')

const props = defineProps<{
  title?: string
  code_txt: string
}>()

const TOOLTIP_DISPLAY_DURATION = 8000
const MAX_LINES = 10

const showMessage = ref(false)
const errorMessage = ref('')
const isExpanded = ref(false)
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

const codeLines = computed(() => props.code_txt.split('\n'))
const displayedCode = computed(() => {
  if (isExpanded.value || codeLines.value.length <= MAX_LINES) {
    return props.code_txt
  }
  return codeLines.value.slice(0, MAX_LINES).join('\n')
})
const shouldShowToggle = computed(() => codeLines.value.length > MAX_LINES)

const toggleExpansion = () => {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <CmkHeading v-if="title" type="h4" class="cmk-code__heading">{{ title }}</CmkHeading>
  <div class="code_wrapper">
    <div class="code_container" :class="{ 'has-toggle': shouldShowToggle, expanded: isExpanded }">
      <CmkScrollContainer type="outer" class="code_scroll_container">
        <pre><code v-text="displayedCode"></code></pre>
      </CmkScrollContainer>
      <div v-if="shouldShowToggle && !isExpanded" class="fade_overlay"></div>
      <div v-if="shouldShowToggle" class="toggle_button_container">
        <CmkButton variant="secondary" class="toggle_button" @click="toggleExpansion">
          <CmkIcon
            name="tree-closed"
            variant="inline"
            size="small"
            class="toggle_icon"
            :class="{ expanded: isExpanded }"
          />
          {{
            isExpanded ? t('cmk-code-show-less', 'Show less') : t('cmk-code-show-more', 'Show more')
          }}
        </CmkButton>
      </div>
    </div>
    <TooltipProvider>
      <Tooltip :open="showMessage" disable-hover-trigger>
        <TooltipTrigger as-child @click="copyToClipboard">
          <CmkIconButton name="copied" size="medium" class="copy_button" />
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
  align-items: flex-start;
  margin-bottom: var(--spacing);
  gap: 8px;
  max-width: 100%;

  .code_container {
    position: relative;
    font-family: monospace;
    font-size: var(--font-size-normal, 12px);
    font-style: normal;
    font-weight: 400;
    line-height: normal;
    padding: 8px 12px 4px 12px;
    color: var(--font-color);
    border-radius: var(--border-radius);
    border: var(--border-width-1, 1px) solid var(--code-background-color);
    background: var(--code-background-color);
    max-width: 100%;
    min-width: 0;
    --scroll-bar-thickness: 20px;

    .code_scroll_container {
      overflow-x: auto;
      padding-bottom: 4px; /* Firefox will place the scrollbar on top of it */
    }

    &.has-toggle:not(.expanded) .code_scroll_container {
      /* Add more space to avoid the scrollbar being hidden behind the fade overlay */
      padding-bottom: var(--scroll-bar-thickness);
    }

    pre {
      margin: 0;
      width: 100%;
    }

    .fade_overlay {
      position: absolute;
      z-index: var(--z-index-base);
      bottom: var(--scroll-bar-thickness);
      left: 0;
      right: 0;
      height: 60px;
      background: linear-gradient(transparent, var(--code-background-color));
      pointer-events: none;
    }

    .toggle_button_container {
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      z-index: var(--z-index-base) + 1;
    }

    &:not(.expanded) .toggle_button_container {
      bottom: 28px;
    }

    &.expanded .toggle_button_container {
      position: relative;
      left: auto;
      transform: none;
      margin-top: 8px;
      text-align: center;
      width: 100%;
    }

    .toggle_button {
      font-size: var(--font-size-normal);
      padding: 0px 8px;
      border-color: var(--font-color);
      color: var(--font-color);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .toggle_icon {
      flex-shrink: 0;
      transition: transform 0.2s ease;

      &.expanded {
        transform: rotate(-90deg);
      }

      &:not(.expanded) {
        transform: rotate(90deg);
      }
    }
  }

  .copy_button {
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
  background-color: var(--code-background-color);
  color: var(--font-color);
  white-space: nowrap;
  position: relative;
  z-index: var(--z-index-tooltip);

  &.error {
    background-color: var(--error-msg-bg-color);
  }
}
</style>
