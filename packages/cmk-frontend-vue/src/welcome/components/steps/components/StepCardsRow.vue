<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts"></script>

<template>
  <div class="welcome-step-cards-row">
    <slot />
  </div>
</template>

<style scoped>
.welcome-step-cards-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}
</style>
