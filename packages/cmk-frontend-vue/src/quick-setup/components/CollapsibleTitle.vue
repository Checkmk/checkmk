<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import InlineChevron from './InlineChevron.vue'
import HelpText from '@/components/HelpText.vue'

interface CollapsibleTitleProps {
  /**@property {string} title - Text to display next to the chevron */
  title: string

  /** @property {boolean} open - If true, the collapsible element will be open by default,
   * otherwise it will be rendered closed
   */
  open: boolean

  /**@property {string} help_text - Help text to display next to the title */
  help_text: string | null
}

defineProps<CollapsibleTitleProps>()
defineEmits(['toggleOpen'])
</script>

<template>
  <button class="qs-collapsible-title" @click="$emit('toggleOpen')">
    <InlineChevron :variant="open ? 'bottom' : 'right'" />
    <span class="qs-collapsible-title__text">
      {{ title }}
    </span>
    <HelpText v-if="help_text" :help="help_text" />
  </button>
</template>

<style scoped>
.qs-collapsible-title {
  position: relative;
  left: -27px;
  background: none;
  border: none;
  cursor: pointer;

  &:hover {
    background-color: transparent;
  }
}

.qs-collapsible-title__text {
  color: var(--font-color);
  font-weight: var(--font-weight-bold);
}

.qs-collapsible-title ::v-deep(.help-text__trigger) {
  margin-left: var(--spacing);
}
</style>
