<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkHelpText from '@/components/CmkHelpText.vue'

interface CollapsibleTitleProps {
  /**@property {TranslatedString} title - Text to display next to the chevron */
  title: TranslatedString

  /**@property {TranslatedString} sideTitle - Text to display on the right side of the title */
  sideTitle?: TranslatedString

  /** @property {boolean} open - If true, the collapsible element will be open by default,
   * otherwise it will be rendered closed
   */
  open: boolean

  /**@property {TranslatedString} help_text - Help text to display next to the title */
  help_text?: TranslatedString | null
}

defineProps<CollapsibleTitleProps>()
defineEmits(['toggleOpen'])
</script>

<template>
  <button class="cmk-collapsible-title" @click.prevent="$emit('toggleOpen')">
    <span
      class="cmk-collapsible-title__chevron"
      :class="`cmk-collapsible-title__chevron--${open ? 'bottom' : 'right'}`"
    />
    <span class="cmk-collapsible-title__text">
      {{ title }}
    </span>
    <span v-if="sideTitle" class="cmk-collapsible-title__side-text">
      {{ sideTitle }}
    </span>
    <span class="cmk-collapsible-title__help">
      <CmkHelpText v-if="help_text" :help="help_text" />
    </span>
  </button>
</template>

<style scoped>
.cmk-collapsible-title {
  display: flex;
  align-items: center;
  position: relative;
  margin-left: 0;
  padding-left: 0;
  background: none;
  border: none;
  cursor: pointer;

  &:hover {
    background-color: transparent;
  }
}

.cmk-collapsible-title__text {
  color: var(--font-color);
  font-weight: var(--font-weight-bold);
}

.cmk-collapsible-title__help {
  margin-left: var(--spacing);
}

.cmk-collapsible-title__chevron {
  display: inline-block;
  width: 8px;
  margin-right: var(--spacing-half);

  &::before {
    border-color: var(--success-dimmed);
    border-style: solid;
    border-width: 1px 1px 0 0;
    content: '';
    display: inline-block;
    width: 5px;
    height: 5px;
    position: relative;
    top: 0.15em;
    transform: rotate(-45deg);
    vertical-align: top;
  }

  &.cmk-collapsible-title__chevron--bottom {
    padding-left: 3px;

    &::before {
      top: 2px;
      transform: rotate(135deg);
      transition: transform 100ms linear;
    }
  }

  &.cmk-collapsible-title__chevron--right::before {
    top: 4px;
    left: 0;
    transform: rotate(45deg);
    transition: transform 100ms linear;
  }
}

.cmk-collapsible-title__side-text {
  color: var(--font-color-dimmed);
  font-weight: var(--font-weight-default);
  margin-left: auto;
}
</style>
