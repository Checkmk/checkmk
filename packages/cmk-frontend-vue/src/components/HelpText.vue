<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import CmkIcon from './CmkIcon.vue'

const props = defineProps<{
  help: string
}>()

const open = ref(false)
const helpIcon = useTemplateRef('helpIcon')

const checkClosing = (e: MouseEvent) => {
  e.preventDefault()
  e.stopPropagation()
  if (e.target !== helpIcon.value) {
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
        data-testid="help-tooltip-trigger"
        class="help-text__trigger"
        @click="(e: MouseEvent) => triggerHelp(e)"
      >
        <CmkIcon
          ref="helpIcon"
          name="info"
          size="xsmall"
          :style="open ? 'transform: scale(1.1);background-color:var(--tag-added-color-light)' : ''"
          class="help-text__icon"
          data-testid="help-icon"
      /></TooltipTrigger>
      <TooltipContent
        side="top"
        align="start"
        class="help-text__content"
        @pointer-down-outside="(e: Event) => checkClosing(e as MouseEvent)"
        @escape-key-down="closeHelp"
      >
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-html="props.help"></div>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>

<style scoped>
body.show_help .help-text__trigger,
body.show_help .help-text__icon {
  display: none;
}

.help-text__trigger {
  margin: 0;
  margin-right: var(--spacing);
  padding: 0;
  border: none;
  background: none;

  .help-text__icon {
    background-color: var(--default-tooltip-icon-color);
    padding: 2px;
    border-radius: 50%;
  }
}
</style>
<style>
.help-text__content {
  max-height: 10rem;
  overflow-y: auto;
  text-wrap: wrap;

  background-color: var(--default-tooltip-background-color);
  border-radius: 0.375rem;

  min-width: 50rem;
  max-width: 50rem;

  color: var(--default-tooltip-text-color);
  box-shadow:
    0 4px 6px rgba(0, 0, 0, 0.1),
    0 2px 4px rgba(0, 0, 0, 0.06);
  margin-left: 0.2rem;
  padding: 1rem;

  .text {
    line-height: 1.2;
  }
}

*::-webkit-scrollbar {
  width: 8px;
}

*::-webkit-scrollbar-track {
  background: var(--custom-scroll-bar-backgroud-color);
  border-top-right-radius: 0.25rem;
  border-bottom-right-radius: 0.25rem;
}

*::-webkit-scrollbar-thumb {
  background-color: var(--custom-scroll-bar-thumb-color);
  border-radius: 1rem;
  border: 3px solid var(--custom-scroll-bar-thumb-border-color);
}
</style>
