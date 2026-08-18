<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { GraphSkeleton } from '@/graphing'
</script>

<template>
  <!-- How many graphs a service has is unknown until the discovery answers, so the wait is
       filled with the one panel a service most often has. -->
  <GraphSkeleton />
</template>
