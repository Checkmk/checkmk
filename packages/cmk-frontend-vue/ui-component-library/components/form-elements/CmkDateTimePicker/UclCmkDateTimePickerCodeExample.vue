<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkDateTimePicker from '@/components/CmkDateTimePicker/CmkDateTimePicker.vue'

const date = ref('2026-03-15')
const time = ref('14:30')
</script>

<template>
  <CmkDateTimePicker v-model:date="date" v-model:time="time" mode="datetime" suffix="UTC+1" />
</template>
