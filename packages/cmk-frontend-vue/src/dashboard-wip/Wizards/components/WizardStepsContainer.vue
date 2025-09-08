<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <div class="create-edit-dashlet__steps-container">
    <slot />
  </div>
</template>

<style scoped>
.create-edit-dashlet__steps-container {
  flex: 1;
  background-color: var(--ux-theme-3);
  padding-top: var(--spacing);
  padding-bottom: var(--spacing);
  padding-left: var(--spacing);
  height: 100%;
  gap: 0;
}
</style>
