<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import { getUserFrontendConfig } from '@/lib/userConfig'

import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

import CmkHtml from './CmkHtml.vue'
import CmkIconButton from './CmkIconButton.vue'
import CmkScrollContainer from './CmkScrollContainer.vue'

defineOptions({
  inheritAttrs: false
})

const props = defineProps<{
  help: TranslatedString
  ariaLabel?: string | undefined
}>()

const open = ref(false)
const triggerRef = ref<InstanceType<typeof CmkIconButton> | null>(null)

const checkClosing = (e: MouseEvent) => {
  e.preventDefault()
  e.stopPropagation()
  if (
    triggerRef.value &&
    triggerRef.value.$el !== (e.target as HTMLElement) &&
    !triggerRef.value.$el.contains(e.target as HTMLElement)
  ) {
    open.value = false
  }
}

const triggerHelp = (e: MouseEvent) => {
  e.preventDefault()
  e.stopPropagation()
  open.value = !open.value
}

const closeHelp = () => {
  open.value = false
}

const hideHelpIcon = getUserFrontendConfig()?.hide_contextual_help_icon ?? false
</script>

<template>
  <CmkTooltipProvider v-if="!!props.help && !hideHelpIcon">
    <CmkTooltip :open="open" disable-closing-trigger>
      <CmkTooltipTrigger
        class="cmk-help-text__trigger"
        as-child
        @click="(e: MouseEvent) => triggerHelp(e)"
      >
        <CmkIconButton
          ref="triggerRef"
          :name="open ? 'help-activated' : 'info-circle'"
          size="medium"
          class="cmk-help-text__icon"
          :aria-label="props.ariaLabel || '?'"
        />
      </CmkTooltipTrigger>
      <CmkTooltipContent
        side="top"
        align="start"
        as-child
        avoid-collisions
        class="cmk-help-text__popup"
        @pointer-down-outside="(e: Event) => checkClosing(e as MouseEvent)"
        @escape-key-down="closeHelp"
      >
        <CmkScrollContainer :max-height="'160px'">
          <div class="cmk-help-text__content">
            <CmkHtml :html="props.help" />
          </div>
        </CmkScrollContainer>
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>

<style scoped>
.cmk-help-text__trigger {
  margin-bottom: -2px;
  border: none;
  background: none;
  outline: none;
  cursor: pointer;
  vertical-align: text-top;

  &:focus,
  &:active {
    outline: none;
    box-shadow: none;
  }
}

.cmk-help-text__content {
  background-color: var(--default-tooltip-background-color);
  border-radius: var(--border-radius);
  min-width: 200px;
  max-width: 600px;
  color: var(--default-tooltip-text-color);
  font-weight: var(--font-weight-default);
  text-align: left;
  white-space: normal;
  box-shadow:
    0 4px 6px rgb(0 0 0 / 10%),
    0 2px 4px rgb(0 0 0 / 6%);
  padding: 16px;
}

.cmk-help-text__popup {
  z-index: var(--z-index-tooltip-offset);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
body.inline_help_as_text .cmk-help-text__trigger,
body.inline_help_as_text .cmk-help-text__icon {
  display: none;
}
</style>
