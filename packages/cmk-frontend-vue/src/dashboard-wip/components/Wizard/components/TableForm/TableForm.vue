<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts"></script>

<template>
  <div class="table-form-container">
    <slot />
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.table-form-container {
  display: flex;
  flex-direction: column;
  row-gap: var(--spacing-half);
}
</style>
