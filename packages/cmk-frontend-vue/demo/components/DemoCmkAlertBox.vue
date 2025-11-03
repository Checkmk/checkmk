<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox from '@/components/CmkAlertBox.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  Variants:
  <ul>
    <li><CmkAlertBox variant="success">This is the success variant</CmkAlertBox></li>
    <li><CmkAlertBox variant="info">This is the info variant</CmkAlertBox></li>
    <li><CmkAlertBox variant="warning">This is the warning variant</CmkAlertBox></li>
    <li><CmkAlertBox variant="error">This is the error variant</CmkAlertBox></li>
  </ul>
  Simple text heading:
  <CmkAlertBox variant="error" heading="Error occurred"> Something went wrong... </CmkAlertBox>
  Rich content heading via slot:
  <CmkAlertBox variant="warning">
    <template #heading> <strong>Warning:</strong> <em>Please review</em> </template>
    Content here...
  </CmkAlertBox>
  Long text:
  <CmkAlertBox variant="success"
    >Very long message in order to showcase the text wrapping and the final position of the text and
    the icon</CmkAlertBox
  >
</template>

<style scoped>
ul {
  list-style-type: none;
  padding: 0;
}

li {
  margin: 1em;
}
</style>
