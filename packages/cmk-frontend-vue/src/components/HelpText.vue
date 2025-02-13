<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/tooltip'
import CmkButton from './CmkButton.vue'
import CmkIcon from './CmkIcon.vue'
import CmkHtml from './CmkHtml.vue'
import CmkScrollContainer from './CmkScrollContainer.vue'

const props = defineProps<{
  help: string
}>()

const open = ref(false)
const triggerRef = ref<InstanceType<typeof CmkIcon> | null>(null)

const checkClosing = (e: MouseEvent) => {
  e.preventDefault()
  e.stopPropagation()
  if (triggerRef.value && (e.target as HTMLElement) !== triggerRef.value.$el) {
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
</script>

<template>
  <TooltipProvider v-if="!!props.help">
    <Tooltip :open="open" disable-closing-trigger>
      <TooltipTrigger
        class="help-text__trigger"
        as-child
        @click="(e: MouseEvent) => triggerHelp(e)"
      >
        <CmkButton :variant="'transparent'" aria-label="?">
          <CmkIcon
            ref="triggerRef"
            :name="open ? 'icon_help_activated' : 'icon_info_circle'"
            size="medium"
            class="help-text__icon"
          />
        </CmkButton>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        align="start"
        as-child
        @pointer-down-outside="(e: Event) => checkClosing(e as MouseEvent)"
        @escape-key-down="closeHelp"
      >
        <CmkScrollContainer :max-height="'160px'">
          <div class="help-text__content">
            <CmkHtml :html="props.help" />
          </div>
        </CmkScrollContainer>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>

<style scoped>
body.inline_help_as_text .help-text__trigger,
body.inline_help_as_text .help-text__icon {
  display: none;
}

.help-text__trigger {
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

.help-text__content {
  background-color: var(--default-tooltip-background-color);
  border-radius: var(--border-radius);

  min-width: 200px;
  max-width: 600px;

  color: var(--default-tooltip-text-color);
  box-shadow:
    0 4px 6px rgba(0, 0, 0, 0.1),
    0 2px 4px rgba(0, 0, 0, 0.06);
  padding: 16px;

  .text {
    line-height: 1.2;
  }
}
</style>
