<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Actions that do not earn a button of their own, behind one quiet trigger.

The listing uses it twice -- per map row and over the list as a whole -- and the
menu is portalled out of whatever opens it, so its styles cannot be scoped:
having them in one place is what keeps the two from drifting apart.

The caller fills the ``default`` slot with ``DropdownMenuItem``s and styles them
through ``maps-overflow-menu__item``, a ``DropdownMenuSeparator`` between groups
through ``maps-overflow-menu__separator``.
-->
<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import {
  DropdownMenuContent,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuTrigger
} from 'reka-ui'

/** What the trigger is called -- it carries no visible text. */
defineProps<{ label: TranslatedString }>()
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger as-child>
      <CmkIconButton
        class="maps-overflow-menu__trigger"
        name="more-actions"
        size="small"
        :primary-color="{ custom: 'var(--maps-overflow-menu-color)' }"
        :title="label"
        :aria-label="label"
      />
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent class="cmk-vue-app maps-overflow-menu" align="end" :side-offset="4">
        <slot />
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>

<style scoped>
/* Dimmed like the other secondary text around it, full strength once aimed at.
   Nested under the block to outweigh CmkIconButton's own padding reset. The
   target is 24px square although the icon is 12px -- the smallest target WCAG
   2.5.8 allows. */
.maps-overflow-menu__trigger.maps-overflow-menu__trigger {
  --maps-overflow-menu-color: var(--font-color-dimmed);

  align-items: center;
  justify-content: center;
  width: var(--dimension-8);
  height: var(--dimension-8);
  padding: 0;
  border-radius: var(--border-radius);
  transition: background-color 0.15s;
}

.maps-overflow-menu__trigger:hover,
.maps-overflow-menu__trigger[data-state='open'] {
  --maps-overflow-menu-color: var(--font-color);

  background: var(--input-hover-bg-color);
}
</style>

<style>
/* The menu is portalled out of this component, so its styles cannot be scoped. */
.maps-overflow-menu {
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

/* 28px rows, so an entry is an easy target rather than a line of text. */
.maps-overflow-menu__item {
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
  user-select: none;

  &[data-highlighted] {
    background-color: var(--ux-theme-3);
  }
}

.maps-overflow-menu__separator {
  height: 1px;
  margin: var(--dimension-2) 0;
  background: var(--ux-theme-6);
}
</style>
