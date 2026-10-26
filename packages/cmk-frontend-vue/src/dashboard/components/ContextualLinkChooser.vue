<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Lets a click on a widget element choose among its links. The menu is portalled, so it opens
from inside SVG figures too. The slot is the trigger, so the caller renders and styles it.
-->
<script setup lang="ts">
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuTrigger
} from 'reka-ui'

import type { ContextualLinkEntry } from '@/dashboard/lib/contextualLinkUrl'

import HtmlBoundary from './HtmlBoundary.vue'

defineProps<{
  entries: ContextualLinkEntry[]
  /** Opens the menu below this element instead of below the trigger. */
  reference?: HTMLElement | null | undefined
  inSvg?: boolean
}>()

const open = defineModel<boolean>('open', { default: false })
</script>

<template>
  <DropdownMenuRoot v-model:open="open" :modal="false">
    <DropdownMenuTrigger as-child>
      <slot />
    </DropdownMenuTrigger>
    <HtmlBoundary :in-svg="inSvg">
      <DropdownMenuPortal>
        <DropdownMenuContent
          class="cmk-vue-app db-contextual-link-chooser"
          :side-offset="4"
          v-bind="reference ? { reference, align: 'start' } : {}"
        >
          <DropdownMenuItem v-for="(entry, index) in entries" :key="index" as-child>
            <a :href="entry.href" class="db-contextual-link-chooser__item">{{ entry.title }}</a>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </HtmlBoundary>
  </DropdownMenuRoot>
</template>

<style>
/* The menu is portalled out of this component, so its styles cannot be scoped. */
.db-contextual-link-chooser {
  display: flex;
  z-index: var(--z-index-modal);
  flex-direction: column;
  min-width: 180px;
  padding: var(--dimension-2);
  background: var(--ux-theme-1);
  border: 1px solid var(--ux-theme-6);
  border-radius: var(--border-radius);
  box-shadow: 0 2px 8px rgb(0 0 0 / 30%);
}

.db-contextual-link-chooser__item {
  display: flex;
  align-items: center;
  min-height: var(--dimension-9);
  padding: 0 var(--dimension-4);
  color: inherit;
  text-decoration: none;
  white-space: nowrap;
  border-radius: var(--dimension-2);
  outline: none;
  cursor: pointer;

  &[data-highlighted] {
    background-color: var(--ux-theme-3);
  }
}
</style>
