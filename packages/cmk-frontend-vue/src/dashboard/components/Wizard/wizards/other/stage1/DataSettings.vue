<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'

const { _t } = usei18n()

interface Props {
  label: TranslatedString
}

defineProps<Props>()
</script>

<template>
  <div>
    <CmkCatalogPanel :title="_t('Data settings')">
      <TableForm>
        <TableFormRow>
          <FieldDescription>{{ label }}</FieldDescription>
          <FieldComponent>
            <slot />
          </FieldComponent>
        </TableFormRow>
      </TableForm>
    </CmkCatalogPanel>
  </div>
</template>
