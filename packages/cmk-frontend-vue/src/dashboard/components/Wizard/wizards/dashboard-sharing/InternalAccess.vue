<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkCode from '@/components/CmkCode.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import ContentSpacer from '../../components/ContentSpacer.vue'

const { _t } = usei18n()

interface InternalAccessProps {
  dashboardUrl: string
}

defineProps<InternalAccessProps>()
</script>

<template>
  <CmkCatalogPanel :title="_t('Internal access')" variant="padded">
    <CmkHeading type="h2">{{
      _t('Users with access permissions can view this dashboard')
    }}</CmkHeading>

    <ContentSpacer />

    <CmkCode
      :title="_t('Dashboard url')"
      :code_txt="dashboardUrl"
      class="db-internal-access__url"
    />
  </CmkCatalogPanel>
</template>

<style scoped>
.db-internal-access__url {
  width: calc(100% - 50px);
}
</style>
