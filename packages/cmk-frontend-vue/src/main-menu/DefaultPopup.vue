<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts"></script>

<template>
  <div class="main-menu-popup-menu"><slot /></div>
</template>

<style scoped>
.main-menu-popup-menu {
  position: absolute;
  top: 58px;
  bottom: 0;
  left: 0;
  min-width: 360px;
  padding-bottom: 20px;
  background-color: rgb(32, 39, 46);
  border-right: 4px solid var(--success);
}
</style>
