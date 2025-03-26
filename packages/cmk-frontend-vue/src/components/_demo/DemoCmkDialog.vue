<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDialog from '@/components/CmkDialog.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <CmkDialog
    :title="'Title'"
    :message="'Some message, dismissal will be stored in currently logged in user based on key.'"
    :buttons="[{ title: 'Button 1', onclick: () => console.log('foo'), variant: 'info' }]"
    :dismissal_button="{ title: 'Dismiss', key: 'key' }"
  />
</template>
