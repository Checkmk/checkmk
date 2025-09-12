<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts"></script>

<template>
  <div class="table-form-row">
    <div class="field-description">
      <span class="field-description__label">
        <slot />
      </span>
    </div>
  </div>
</template>

<style scoped>
.table-form-row {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
}

.field-description {
  flex: 1;
  direction: ltr;
  overflow-wrap: break-word;
  overflow: hidden;
  text-align: left;
  text-wrap-mode: nowrap;
}

.field-description__label {
  width: 100%;
  display: block;
}
</style>
