<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDialog from '@/components/CmkDialog.vue'

function handleAction() {
  console.log('Action triggered')
}
</script>

<template>
  <CmkDialog
    variant="info"
    title="Dialog Title"
    message="This is an informational message that requires user attention."
    :buttons="[{ title: 'Acknowledge', variant: 'info', onclick: handleAction }]"
    :dismissal-button="{ title: 'Dismiss', key: 'immediate_slideout_change' }"
  />
</template>
