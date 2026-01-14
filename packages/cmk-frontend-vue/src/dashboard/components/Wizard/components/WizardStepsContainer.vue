<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <div class="db-wizard-steps-container">
    <slot />
  </div>
</template>

<style scoped>
.db-wizard-steps-container {
  flex: 1;
  background-color: var(--slide-in-left-part);
  padding-top: var(--spacing);
  padding-bottom: var(--spacing);
  padding-left: var(--spacing);
  height: calc(100% - var(--spacing) * 2);
  gap: 0;
}
</style>
