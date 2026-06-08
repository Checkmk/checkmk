<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import { CmkRadioButton, CmkRadioGroup } from '@/components/user-input/CmkRadioButton'

const selected = ref('custom')
</script>

<template>
  <CmkRadioGroup v-model="selected" label="Time range">
    <CmkRadioButton value="today" label="Today" />
    <CmkRadioButton value="yesterday" label="Yesterday" />
    <CmkRadioButton value="week" label="This week" help="The current calendar week." />
    <CmkRadioButton value="month" label="This month" />
    <CmkRadioButton value="year" label="This year" disabled />
    <CmkRadioButton value="custom" label="Custom" />
  </CmkRadioGroup>
</template>
