<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

const props = defineProps<{
  help: string
}>()

const open = ref(false)

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
    <Tooltip :open="open">
      <TooltipTrigger
        data-testid="help-tooltip-trigger"
        class="trigger"
        @click="(e: MouseEvent) => triggerHelp(e)"
      >
        <img
          :style="open ? 'transform: scale(1.1);background-color:var(--tag-added-color-light)' : ''"
          class="help-text"
          data-testid="help-icon"
          @click="triggerHelp"
      /></TooltipTrigger>
      <TooltipContent
        side="top"
        align="start"
        class="help-content"
        @pointer-down-outside="closeHelp"
        @escape-key-down="closeHelp"
      >
        {{ props.help }}
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>

<style scoped>
.help-text {
  padding-left: 5px;
  display: none;
}

.trigger {
  margin-left: 0.25rem;
  margin: 0;
  padding: 0;
  border: none;
  background: none;
  margin-left: 0.5rem;

  img {
    content: var(--icon-help);
    width: 10px;
    height: 10px;
    background-color: var(--default-tooltip-icon-color);
    padding: 2px;
    border-radius: 50%;
    cursor: pointer;
    margin-bottom: -3px;
  }
}

body:not(.show_help) {
  .help-text {
    display: inline;
  }
}
</style>
<style>
.help-content {
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
