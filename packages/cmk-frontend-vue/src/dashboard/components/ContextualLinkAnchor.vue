<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Makes its slot a link: one entry leads straight to it, several open a menu of them, none leave
the slot as it is. The slot learns whether there are several, so it can show the menu arrow.
-->
<script setup lang="ts">
import type { ContextualLinkEntry } from '@/dashboard/lib/contextualLinkUrl'

import ContextualLinkChooser from './ContextualLinkChooser.vue'

defineProps<{
  entries: ContextualLinkEntry[]
  title?: string | undefined
}>()

defineSlots<{ default(props: { several: boolean }): unknown }>()
</script>

<template>
  <a
    v-if="entries.length === 1"
    class="db-contextual-link-anchor"
    :href="entries[0]!.href"
    :title="title"
  >
    <slot :several="false" />
  </a>
  <ContextualLinkChooser v-else-if="entries.length > 1" :entries="entries">
    <a role="button" tabindex="0" class="db-contextual-link-anchor" :title="title">
      <slot :several="true" />
    </a>
  </ContextualLinkChooser>
  <slot v-else :several="false" />
</template>

<style>
/* Unscoped: the text and the arrow are the callers' slot content, in HTML and in SVG figures. */
.db-contextual-link-anchor {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  max-width: 100%;
  color: inherit;
  text-decoration: none;
  cursor: pointer;
}

.db-contextual-link-anchor__text {
  font-weight: var(--font-weight-semibold);
}

.db-contextual-link-anchor__arrow {
  display: inline-block;
  vertical-align: middle;
  opacity: 0.7;
}

.db-contextual-link-anchor:is(:hover, :focus-visible, [data-state='open']) {
  .db-contextual-link-anchor__text {
    text-decoration: underline;
  }

  .db-contextual-link-anchor__arrow {
    opacity: 1;
  }
}
</style>
