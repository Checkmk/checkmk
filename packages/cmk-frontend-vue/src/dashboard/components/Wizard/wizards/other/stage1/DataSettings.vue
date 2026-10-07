<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'

const { _t } = usei18n()
</script>

<template>
  <div>
    <CmkCatalogPanel :title="_t('Data settings')" variant="padded">
      <TableForm>
        <slot />
      </TableForm>
    </CmkCatalogPanel>
  </div>
</template>
