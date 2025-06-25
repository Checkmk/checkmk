<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkBadge from '../CmkBadge.vue'
import CmkIcon from '@/components/CmkIcon.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <h2>Small</h2>
  <CmkBadge size="small">1</CmkBadge>
  <CmkBadge size="small" color="success">1</CmkBadge>
  <CmkBadge size="small" color="warning">1</CmkBadge>
  <CmkBadge size="small" color="danger">1</CmkBadge>

  <h2>Medium</h2>
  <CmkBadge>1</CmkBadge>
  <CmkBadge color="success"><CmkIcon size="large" name="checkmark"></CmkIcon></CmkBadge>
  <CmkBadge color="warning">a</CmkBadge>
  <CmkBadge color="danger"><CmkIcon size="small" name="check"></CmkIcon></CmkBadge>

  <h2>Large</h2>
  <CmkBadge size="large">1</CmkBadge>
  <CmkBadge size="large" color="success"
    ><CmkIcon size="xlarge" name="checkmark"></CmkIcon
  ></CmkBadge>
  <CmkBadge size="large" color="warning">2</CmkBadge>
  <CmkBadge size="large" color="danger">33</CmkBadge>
</template>

<style scoped>
h2 {
  margin: 16px 0;
}
</style>
