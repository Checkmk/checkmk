<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <h2>Box (width/height: 100%)</h2>
  <div class="demo-cmk-skeleton">
    <CmkSkeleton></CmkSkeleton>
  </div>

  <h2>Text-Skeletons</h2>
  <ul>
    <li><label>h1</label><CmkSkeleton type="h1"></CmkSkeleton></li>
    <li><label>h2</label><CmkSkeleton type="h2"></CmkSkeleton></li>
    <li><label>h3</label><CmkSkeleton type="h3"></CmkSkeleton></li>
    <li><label>text</label><CmkSkeleton type="text"></CmkSkeleton></li>
    <li><label>info-text</label><CmkSkeleton type="info-text"></CmkSkeleton></li>
  </ul>

  <h2>Icon-Skeletons</h2>
  <ul>
    <li><label>xsmall</label><CmkSkeleton type="icon-xsmall"></CmkSkeleton></li>
    <li><label>small</label><CmkSkeleton type="icon-small"></CmkSkeleton></li>
    <li><label>medium</label><CmkSkeleton type="icon-medium"></CmkSkeleton></li>
    <li><label>large</label><CmkSkeleton type="icon-large"></CmkSkeleton></li>
    <li><label>xlarge</label><CmkSkeleton type="icon-xlarge"></CmkSkeleton></li>
    <li><label>xxlarge</label><CmkSkeleton type="icon-xxlarge"></CmkSkeleton></li>
    <li><label>xxxlarge</label><CmkSkeleton type="icon-xxxlarge"></CmkSkeleton></li>
  </ul>

  <h2>Slotted Skeletons</h2>
  <div class="demo-cmk-skeleton">
    <CmkSkeleton>
      <ul>
        <li><CmkSkeleton type="h1"></CmkSkeleton></li>
        <li><CmkSkeleton type="h2"></CmkSkeleton></li>
        <li><CmkSkeleton type="h3"></CmkSkeleton></li>
        <li><CmkSkeleton type="text"></CmkSkeleton></li>
        <li><CmkSkeleton type="info-text"></CmkSkeleton></li>
      </ul>
    </CmkSkeleton>
  </div>
</template>

<style scoped>
.demo-cmk-skeleton {
  width: 200px;
  height: 100px;
  min-width: 200px;
  min-height: 110px;
  padding: 10px;
}

li {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  margin-bottom: 5px;

  label {
    width: 100px;
  }
}
</style>
