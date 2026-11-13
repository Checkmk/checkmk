<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <tr class="monitoring-table-row">
    <slot />
  </tr>
</template>

<style scoped>
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-table-row:hover :deep(td) {
  background-color: var(--background-row-hover-highlight);
}
</style>
