<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One entry of a MapsMenu: a button, or -- given ``href`` -- a link that opens in
a new tab. The caller puts the icon and the text in the ``default`` slot.

Checkmk styles buttons and links page-wide, so the entry resets what it would
inherit from there, the way CmkIconButton does, and stays a plain row.
-->
<script setup lang="ts">
defineProps<{
  href?: string | null | undefined
  /** For an entry that removes something. */
  danger?: boolean
}>()
</script>

<template>
  <a
    v-if="href"
    :href="href"
    target="_blank"
    rel="noopener noreferrer"
    role="menuitem"
    class="maps-menu-item"
    :class="{ 'maps-menu-item--danger': danger }"
  >
    <slot />
  </a>
  <button
    v-else
    type="button"
    role="menuitem"
    class="maps-menu-item"
    :class="{ 'maps-menu-item--danger': danger }"
  >
    <slot />
  </button>
</template>

<style scoped>
.maps-menu-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  box-sizing: border-box;
  width: 100%;
  margin: 0;
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: inherit;
  letter-spacing: inherit;
  color: var(--font-color-dimmed);
  text-align: left;
  text-decoration: none;
  background: none;
  border: none;
  border-radius: 0;
  cursor: pointer;
  transition:
    color 0.15s,
    background-color 0.15s;
}

/* Outweighs Checkmk's `body.main a:link`, which would paint a link entry white. */
.maps-menu-item:any-link {
  color: var(--font-color-dimmed);
}

.maps-menu-item:hover {
  color: var(--font-color);
  background: var(--input-hover-bg-color);
}

.maps-menu-item:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

.maps-menu-item--danger,
.maps-menu-item--danger:hover {
  color: var(--color-light-red-40);
}

.maps-menu-item--danger:hover {
  background: color-mix(in srgb, var(--color-light-red-50) 8%, transparent);
}
</style>
