<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <div class="db-data-selection-container__container">
    <slot />
  </div>
</template>

<style scoped>
.db-data-selection-container__container {
  padding: 0 var(--dimension-3);
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
