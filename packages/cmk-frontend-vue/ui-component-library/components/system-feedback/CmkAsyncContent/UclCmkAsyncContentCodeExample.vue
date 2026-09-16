<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAsyncContent from 'cmk-ui-library/components/CmkAsyncContent'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import { markRaw, ref } from 'vue'

// The page owns what is rendered and how it is loaded; the body does the rest,
// so the container it sits in is left with nothing to arrange.
import HostOverview from '../../content-organization/CmkSlideInTabbed/CmkSlideInTabbedDemoTab.vue'

const openHost = ref<string | null>(null)

function loadHost(): Promise<{ loadedAt: string }> {
  return Promise.resolve({ loadedAt: new Date().toLocaleTimeString() })
}
</script>

<template>
  <CmkButton @click="openHost = 'my-host'">Open slide-in</CmkButton>

  <!-- The body loads on mount, so closing the panel is all it takes for the
       next opening to start from a fresh read. -->
  <CmkSlideInDialog
    :open="openHost !== null"
    :header="{ title: 'Host overview', closeButton: true }"
    @close="openHost = null"
  >
    <CmkAsyncContent
      v-if="openHost"
      :component="markRaw(HostOverview)"
      :props="{ label: openHost }"
      :load="loadHost"
    />
  </CmkSlideInDialog>
</template>
