<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkChip from '../CmkChip.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <h1>Size</h1>
  <h2>Small</h2>
  <CmkChip size="small" content="1"></CmkChip>
  <CmkChip size="small" content="some long content"></CmkChip>
  <h2>Medium</h2>
  <CmkChip content="1"></CmkChip>
  <CmkChip content="some long content"></CmkChip>
  <h2>Large</h2>
  <CmkChip size="large" content="1"></CmkChip>
  <CmkChip size="large" content="some long content"></CmkChip>
  <h1>Color and Variant</h1>
  <div class="matrix-container">
    <table class="chip-matrix">
      <thead>
        <tr>
          <th>Color / Variant</th>
          <th>Fill</th>
          <th>Outline</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="color-label">Default</td>
          <td><CmkChip color="default" variant="fill" content="Default Fill"></CmkChip></td>
          <td><CmkChip color="default" variant="outline" content="Default Outline"></CmkChip></td>
        </tr>
        <tr>
          <td class="color-label">Success</td>
          <td><CmkChip color="success" variant="fill" content="Success Fill"></CmkChip></td>
          <td><CmkChip color="success" variant="outline" content="Success Outline"></CmkChip></td>
        </tr>
        <tr>
          <td class="color-label">Warning</td>
          <td><CmkChip color="warning" variant="fill" content="Warning Fill"></CmkChip></td>
          <td><CmkChip color="warning" variant="outline" content="Warning Outline"></CmkChip></td>
        </tr>
        <tr>
          <td class="color-label">Danger</td>
          <td><CmkChip color="danger" variant="fill" content="Danger Fill"></CmkChip></td>
          <td><CmkChip color="danger" variant="outline" content="Danger Outline"></CmkChip></td>
        </tr>
      </tbody>
    </table>
  </div>

  <h1>Individual Examples</h1>
  <h2>Colors (default outline variant)</h2>
  <CmkChip color="default" content="Default"></CmkChip>
  <CmkChip color="success" content="Success"></CmkChip>
  <CmkChip color="warning" content="Warning"></CmkChip>
  <CmkChip color="danger" content="Danger"></CmkChip>

  <h2>Variants (default color)</h2>
  <CmkChip variant="fill" content="Fill"></CmkChip>
  <CmkChip variant="outline" content="Outline"></CmkChip>
</template>

<style scoped>
h1,
h2 {
  margin: 16px 0;
}

.matrix-container {
  margin: 20px 0;
}

.chip-matrix {
  border-collapse: collapse;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.chip-matrix th,
.chip-matrix td {
  border: 1px solid var(--ux-theme-1);
  padding: 16px;
  text-align: center;
  vertical-align: middle;
}

.chip-matrix th {
  background-color: var(--ux-theme-2);
  font-weight: bold;
}

.color-label {
  font-weight: 600;
  background-color: var(--ux-theme-3);
  text-align: left;
}

.chip-matrix tr:nth-child(even) {
  background-color: var(--ux-theme-4);
}

.chip-matrix tr:hover {
  background-color: var(--ux-theme-5);
}
</style>
