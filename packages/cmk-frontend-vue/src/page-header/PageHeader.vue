<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// Shared top header for full-page apps (e.g. dashboards, custom graph designer): a top bar with the
// breadcrumb on the left and the refresh control on the right, followed by the page's own menu.
// The refresh slot has zero height, so its control overlaps the menu row instead of pushing it
// down. Positioning such as sticky behaviour is left to the page, via a class on this component.
defineSlots<{
  breadcrumb(): unknown
  refresh(): unknown
  menu(): unknown
}>()
</script>

<template>
  <header class="page-header">
    <div class="page-header__topbar">
      <div class="page-header__breadcrumb">
        <slot name="breadcrumb" />
      </div>
      <div class="page-header__refresh">
        <slot name="refresh" />
      </div>
    </div>

    <slot name="menu" />
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-direction: column;
  padding: var(--dimension-6);
  padding-bottom: 0;
  background: var(--ux-theme-2);
  border-bottom: 1px solid var(--border-color-separator);
}

.page-header__topbar {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-6);
}

.page-header__breadcrumb {
  flex: 1 1 auto;
  min-width: 0;
}

/* Zero height so the control overlaps the row below instead of pushing it down. */
.page-header__refresh {
  flex: 0 0 auto;
  height: 0;
  overflow: visible;
  position: relative;
  z-index: 3;
}
</style>
