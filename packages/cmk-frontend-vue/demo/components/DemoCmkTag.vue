<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkTag from '@/components/CmkTag.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <h1>Size</h1>
  <h2>Small</h2>
  <CmkTag size="small" content="1"></CmkTag>
  <CmkTag size="small" content="some long content"></CmkTag>
  <h2>Medium</h2>
  <CmkTag content="1"></CmkTag>
  <CmkTag content="some long content"></CmkTag>
  <h2>Large</h2>
  <CmkTag size="large" content="1"></CmkTag>
  <CmkTag size="large" content="some long content"></CmkTag>
  <h1>Color and Variant</h1>
  <div class="demo-cmk-tag__matrix-container">
    <table class="demo-cmk-tag__tag-matrix">
      <thead>
        <tr>
          <th>Color / Variant</th>
          <th>Fill</th>
          <th>Outline</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="demo-cmk-tag__color-label">Default</td>
          <td><CmkTag color="default" variant="fill" content="Default Fill"></CmkTag></td>
          <td><CmkTag color="default" variant="outline" content="Default Outline"></CmkTag></td>
        </tr>
        <tr>
          <td class="demo-cmk-tag__color-label">Success</td>
          <td><CmkTag color="success" variant="fill" content="Success Fill"></CmkTag></td>
          <td><CmkTag color="success" variant="outline" content="Success Outline"></CmkTag></td>
        </tr>
        <tr>
          <td class="demo-cmk-tag__color-label">Warning</td>
          <td><CmkTag color="warning" variant="fill" content="Warning Fill"></CmkTag></td>
          <td><CmkTag color="warning" variant="outline" content="Warning Outline"></CmkTag></td>
        </tr>
        <tr>
          <td class="demo-cmk-tag__color-label">Danger</td>
          <td><CmkTag color="danger" variant="fill" content="Danger Fill"></CmkTag></td>
          <td><CmkTag color="danger" variant="outline" content="Danger Outline"></CmkTag></td>
        </tr>
      </tbody>
    </table>
  </div>

  <h1>Individual Examples</h1>
  <h2>Colors (default outline variant)</h2>
  <CmkTag color="default" content="Default"></CmkTag>
  <CmkTag color="success" content="Success"></CmkTag>
  <CmkTag color="warning" content="Warning"></CmkTag>
  <CmkTag color="danger" content="Danger"></CmkTag>

  <h2>Variants (default color)</h2>
  <CmkTag variant="fill" content="Fill"></CmkTag>
  <CmkTag variant="outline" content="Outline"></CmkTag>
</template>

<style scoped>
h1,
h2 {
  margin: 16px 0;
}

.demo-cmk-tag__matrix-container {
  margin: 20px 0;
}

.demo-cmk-tag__tag-matrix {
  border-collapse: collapse;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.demo-cmk-tag__tag-matrix th,
.demo-cmk-tag__tag-matrix td {
  border: 1px solid var(--ux-theme-1);
  padding: 16px;
  text-align: center;
  vertical-align: middle;
}

.demo-cmk-tag__tag-matrix th {
  background-color: var(--ux-theme-2);
  font-weight: bold;
}

.demo-cmk-tag__color-label {
  font-weight: 600;
  background-color: var(--ux-theme-3);
  text-align: left;
}

.demo-cmk-tag__tag-matrix tr:nth-child(even) {
  background-color: var(--ux-theme-4);
}

.demo-cmk-tag__tag-matrix tr:hover {
  background-color: var(--ux-theme-5);
}
</style>
