<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkChip from '@/components/CmkChip.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <h1>Size</h1>
  <h2>Small</h2>
  <CmkChip size="small">
    <template #start><CmkIcon name="alert-crit" size="small" /></template> Some text

    <template #end><CmkIcon name="cancel" size="small" /></template>
  </CmkChip>
  <h2>Medium</h2>
  <CmkChip>
    <template #start><CmkIcon name="alert-crit" /></template> Some text
    <template #end><CmkIcon name="cancel" /></template>
  </CmkChip>
  <h2>Large</h2>
  <CmkChip size="large">
    <template #start><CmkIcon name="alert-crit" size="large" /></template> Some text
    <template #end><CmkIcon name="cancel" size="large" /></template>
  </CmkChip>

  <h1>Non button Chip</h1>
  <CmkChip size="large" :as-div="true">
    <template #start><CmkIcon name="alert-crit" size="large" /></template> Some text
    <template #end><CmkIcon name="cancel" size="large" /></template>
  </CmkChip>

  <h1>Color, Variant and State</h1>
  <div class="demo-cmk-chip__matrix-container">
    <table class="demo-cmk-chip__chip-matrix">
      <thead>
        <tr>
          <th>Color / Variant</th>
          <th>Fill (Default)</th>
          <th>Fill Disabled</th>
          <th>Outline</th>
          <th>Outline Disabled</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="demo-cmk-chip__color-label">Success (Default)</td>
          <td><CmkChip variant="fill">Success Fill</CmkChip></td>
          <td>
            <CmkChip variant="fill" :disabled="true">Success Fill Disabled</CmkChip>
          </td>
          <td><CmkChip variant="outline">Success outline</CmkChip></td>
          <td>
            <CmkChip variant="outline" :disabled="true">Success Fill Disabled</CmkChip>
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Others</td>
          <td><CmkChip color="others" variant="fill">Others Fill</CmkChip></td>
          <td>
            <CmkChip color="others" variant="fill" :disabled="true">Others Fill Disabled</CmkChip>
          </td>
          <td><CmkChip color="others" variant="outline">Others Outline</CmkChip></td>
          <td>
            <CmkChip color="others" variant="outline" :disabled="true"
              >Others Fill Disabled</CmkChip
            >
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Hosts</td>
          <td><CmkChip color="hosts" variant="fill">Hosts Fill</CmkChip></td>
          <td>
            <CmkChip color="hosts" variant="fill" :disabled="true">Hosts Fill Disabled</CmkChip>
          </td>
          <td><CmkChip color="hosts" variant="outline">Hosts Outline</CmkChip></td>
          <td>
            <CmkChip color="hosts" variant="outline" :disabled="true">Hosts Fill Disabled</CmkChip>
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Info</td>
          <td><CmkChip color="info" variant="fill">Info Fill</CmkChip></td>
          <td>
            <CmkChip color="info" variant="fill" :disabled="true">Info Fill Disabled</CmkChip>
          </td>
          <td><CmkChip color="info" variant="outline">Info Outline</CmkChip></td>
          <td>
            <CmkChip color="info" variant="outline" :disabled="true">Info Fill Disabled</CmkChip>
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Warning</td>
          <td><CmkChip color="warning" variant="fill">Warning Fill</CmkChip></td>
          <td>
            <CmkChip color="warning" variant="fill" :disabled="true">Warning Fill Disabled</CmkChip>
          </td>
          <td><CmkChip color="warning" variant="outline">Warning Outline</CmkChip></td>
          <td>
            <CmkChip color="warning" variant="outline" :disabled="true"
              >Warning Fill Disabled</CmkChip
            >
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Services</td>
          <td><CmkChip color="services" variant="fill">Services Fill</CmkChip></td>
          <td>
            <CmkChip color="services" variant="fill" :disabled="true">
              Services Fill Disabled
            </CmkChip>
          </td>
          <td><CmkChip color="services" variant="outline">Services Outline</CmkChip></td>
          <td>
            <CmkChip color="services" variant="outline" :disabled="true">
              Services Fill Disabled
            </CmkChip>
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Danger</td>
          <td><CmkChip color="danger" variant="fill">Danger Fill</CmkChip></td>
          <td>
            <CmkChip color="danger" variant="fill" :disabled="true">Danger Fill Disabled</CmkChip>
          </td>
          <td><CmkChip color="danger" variant="outline">Danger Outline</CmkChip></td>
          <td>
            <CmkChip color="danger" variant="outline" :disabled="true"
              >Danger Fill Disabled</CmkChip
            >
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Customization</td>
          <td><CmkChip color="customization" variant="fill">Customization Fill</CmkChip></td>
          <td>
            <CmkChip color="customization" variant="fill" :disabled="true">
              Customization Fill Disabled
            </CmkChip>
          </td>
          <td><CmkChip color="customization" variant="outline">Customization Outline</CmkChip></td>
          <td>
            <CmkChip color="customization" variant="outline" :disabled="true">
              Customization Fill Disabled
            </CmkChip>
          </td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">Users</td>
          <td><CmkChip color="users" variant="fill">Users Fill</CmkChip></td>
          <td><CmkChip color="users" variant="fill" :disabled="true">Users Fill</CmkChip></td>
          <td><CmkChip color="users" variant="outline">Users Outline</CmkChip></td>
          <td><CmkChip color="users" variant="outline" :disabled="true">Users Fill</CmkChip></td>
        </tr>
        <tr>
          <td class="demo-cmk-chip__color-label">SpecialAgents</td>
          <td><CmkChip color="specialAgents" variant="fill">SpecialAgents Fill</CmkChip></td>
          <td>
            <CmkChip color="specialAgents" variant="fill" :disabled="true">
              SpecialAgents Fill Disabled
            </CmkChip>
          </td>
          <td><CmkChip color="specialAgents" variant="outline">SpecialAgents Outline</CmkChip></td>
          <td>
            <CmkChip color="specialAgents" variant="outline" :disabled="true">
              SpecialAgents Fill Disabled
            </CmkChip>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
h1,
h2 {
  margin: 16px 0;
}

.demo-cmk-chip__matrix-container {
  margin: 20px 0;
}

.demo-cmk-chip__chip-matrix {
  border-collapse: collapse;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.demo-cmk-chip__chip-matrix th,
.demo-cmk-chip__chip-matrix td {
  border: 1px solid var(--ux-theme-1);
  padding: 16px;
  text-align: center;
  vertical-align: middle;
}

.demo-cmk-chip__chip-matrix th {
  background-color: var(--ux-theme-2);
  font-weight: bold;
}

.demo-cmk-chip__color-label {
  font-weight: 600;
  background-color: var(--ux-theme-3);
  text-align: left;
}

.demo-cmk-chip__chip-matrix tr:nth-child(even) {
  background-color: var(--ux-theme-4);
}

.demo-cmk-chip__chip-matrix tr:hover {
  background-color: var(--ux-theme-5);
}
</style>
