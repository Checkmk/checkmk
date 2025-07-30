<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkProgressbar from '@/components/CmkProgressbar.vue'
import usei18n from '@/lib/i18n'

const { t } = usei18n('changes-app')
</script>

<template>
  <span class="cmk-changes-activating-text">{{
    t('activating-changes', 'Activating changes...')
  }}</span>
  <span class="cmk-changes-activating-text">{{
    t('safely-navigate-away', "You can safely navigate away - we'll keep working in the background")
  }}</span>
  <CmkProgressbar max="unknown"></CmkProgressbar>
</template>

<style scoped>
.cmk-changes-activating-text {
  font-weight: var(--font-weight-bold);
}
</style>
