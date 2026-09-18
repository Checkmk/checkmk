<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import StateTag from 'cmk-ui-library/components/StateTag.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <h1>Tone (host)</h1>
  <StateTag label="OK" tone="ok" kind="host" />
  <StateTag label="WARN" tone="warning" kind="host" />
  <StateTag label="CRIT" tone="critical" kind="host" />
  <StateTag label="UNKNOWN" tone="unknown" kind="host" />
  <StateTag label="PENDING" tone="pending" kind="host" />

  <h1>Kind</h1>
  <StateTag label="UP" tone="ok" kind="host" />
  <StateTag label="OK" tone="ok" kind="service" />

  <h1>Size</h1>
  <StateTag label="OK" tone="ok" kind="host" size="default" />
  <StateTag label="OK" tone="ok" kind="host" size="compact" />
  <StateTag label="OK" tone="ok" kind="host" size="inline" />

  <h1>Stale</h1>
  <StateTag label="OK" tone="ok" kind="host" :stale="true" />
</template>
