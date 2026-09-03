<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A multi-line text field in the same shape as the library's single-line one
(``CmkInput``), which has no multi-line variant. Every place in Maps that takes
free text over several lines — a textbox's content, a Livestatus filter —
uses this so they all look and behave alike.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

const { rows = 3, monospace = false } = defineProps<{
  placeholder?: TranslatedString
  rows?: number
  /** For an expression rather than prose: fixed pitch, and no spell check. */
  monospace?: boolean
}>()

const model = defineModel<string>({ required: true })
</script>

<template>
  <textarea
    v-model="model"
    class="maps-text-area"
    :class="{ 'maps-text-area--monospace': monospace }"
    :rows="rows"
    :placeholder="placeholder"
    :spellcheck="!monospace"
  />
</template>

<style scoped>
.maps-text-area {
  width: 100%;
  padding: var(--dimension-3) var(--dimension-4);
  font-family: inherit;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--font-color);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
}

.maps-text-area:focus-visible {
  outline: none;
  border-color: var(--color-corporate-green-50);
}

.maps-text-area--monospace {
  font-family: monospace;
  font-size: var(--font-size-normal);
  line-height: 16px;
}
</style>
