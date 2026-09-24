<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSurfaceNotice from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

function reload() {
  console.log('Retry clicked')
}
</script>

<template>
  <CmkSurfaceNotice
    variant="error"
    :message="_t('Widget data could not be loaded.')"
    :description="_t('Monitoring data source unavailable.')"
    retry
    @retry="reload"
  />
</template>
