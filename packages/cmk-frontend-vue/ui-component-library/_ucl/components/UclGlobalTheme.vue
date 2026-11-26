<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import { computed } from 'vue'

import { type Theme, useTheme } from '../composables/useTheme'

const { currentTheme, setTheme } = useTheme()

const selectedThemeModel = computed({
  get: () => currentTheme.value,
  set: (newTheme: Theme) => setTheme(newTheme)
})

const themeOptions = [
  { name: 'facelift', title: 'Light Mode' },
  { name: 'modern-dark', title: 'Dark Mode' }
]
</script>

<template>
  <CmkDropdown
    v-model="selectedThemeModel"
    :options="{ type: 'fixed', suggestions: themeOptions }"
    label="Theme"
  />
</template>
