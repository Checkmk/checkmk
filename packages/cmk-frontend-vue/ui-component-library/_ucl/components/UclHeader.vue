<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import iconUrl from '../assets/images/checkmk_logo.svg'
import UclGlobalTheme from './UclGlobalTheme.vue'
</script>

<template>
  <div class="ucl-header">
    <div class="ucl-header__item">
      <div class="ucl-header__group">
        <img :src="iconUrl" alt="Checkmk logo" width="117" />
        <span class="ucl-header__app-title">| UI Component Library</span>
      </div>
    </div>
    <div class="ucl-header__item">
      <UclGlobalTheme />
    </div>
  </div>
</template>

<style scoped>
.ucl-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.ucl-header__item {
  display: flex;
  align-items: center;
}

.ucl-header__group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ucl-header__app-title {
  color: var(--color-corporate-green-50);
  font-size: 20px;
  font-weight: 400;
  display: flex;
  align-items: center;
}
</style>
