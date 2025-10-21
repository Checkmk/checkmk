<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkBadge from '@/components/CmkBadge.vue'
import CmkIcon from '@/components/CmkIcon'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <table>
    <thead>
      <tr>
        <th></th>
        <th>Fill</th>
        <th>Outline</th>
        <th>Circle</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <th>Small</th>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge type="fill" size="small">1</CmkBadge>
            <CmkBadge type="fill" size="small" color="success">99+</CmkBadge>
            <CmkBadge type="fill" size="small" color="warning">1</CmkBadge>
            <CmkBadge type="fill" size="small" color="danger">1</CmkBadge>
          </div>
        </td>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge type="outline" size="small">1</CmkBadge>
            <CmkBadge type="outline" size="small" color="success">1</CmkBadge>
            <CmkBadge type="outline" size="small" color="warning">1</CmkBadge>
            <CmkBadge type="outline" size="small" color="danger">1</CmkBadge>
          </div>
        </td>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge shape="circle" size="small">1</CmkBadge>
            <CmkBadge shape="circle" size="small" color="success">1</CmkBadge>
            <CmkBadge shape="circle" size="small" color="warning">1</CmkBadge>
            <CmkBadge shape="circle" size="small" color="danger">1</CmkBadge>
          </div>
        </td>
      </tr>
      <tr>
        <th>Medium</th>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge type="fill">online</CmkBadge>
            <CmkBadge type="fill" color="success">
              <CmkIcon size="large" name="checkmark"></CmkIcon>
            </CmkBadge>
            <CmkBadge type="fill" color="warning">a</CmkBadge>
            <CmkBadge type="fill" color="danger">
              <CmkIcon size="small" name="check"></CmkIcon>
            </CmkBadge>
          </div>
        </td>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge>1</CmkBadge>
            <CmkBadge type="outline" color="success">Ok</CmkBadge>
            <CmkBadge type="outline" color="warning">a</CmkBadge>
            <CmkBadge type="outline" color="danger">
              <CmkIcon size="small" name="check"></CmkIcon>
            </CmkBadge>
          </div>
        </td>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge>1</CmkBadge>
            <CmkBadge type="fill" shape="circle" color="success"
              ><CmkIcon size="large" name="checkmark"></CmkIcon
            ></CmkBadge>
            <CmkBadge shape="circle" color="warning">a</CmkBadge>
            <CmkBadge type="fill" shape="circle" color="danger"
              ><CmkIcon size="small" name="check"></CmkIcon
            ></CmkBadge>
          </div>
        </td>
      </tr>
      <tr>
        <th>Large</th>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge type="fill" size="large">1</CmkBadge>
            <CmkBadge type="fill" size="large" color="success"
              ><CmkIcon size="xxlarge" name="checkmark"></CmkIcon
            ></CmkBadge>
            <CmkBadge type="fill" size="large" color="warning">2</CmkBadge>
            <CmkBadge type="fill" size="large" color="danger">33</CmkBadge>
          </div>
        </td>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge type="outline" size="large">1</CmkBadge>
            <CmkBadge type="outline" size="large" color="success">yes</CmkBadge>
            <CmkBadge type="outline" size="large" color="warning">2</CmkBadge>
            <CmkBadge type="outline" size="large" color="danger">33</CmkBadge>
          </div>
        </td>
        <td>
          <div class="demo-cmk-badge__container">
            <CmkBadge shape="circle" size="large">1</CmkBadge>
            <CmkBadge type="fill" shape="circle" size="large" color="success"
              ><CmkIcon size="xxlarge" name="checkmark"></CmkIcon
            ></CmkBadge>
            <CmkBadge shape="circle" size="large" color="warning">2</CmkBadge>
            <CmkBadge shape="circle" size="large" color="danger">33</CmkBadge>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
table {
  background: var(--ux-theme-6);
  color: var(--color);
}

.demo-cmk-badge__container {
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>
