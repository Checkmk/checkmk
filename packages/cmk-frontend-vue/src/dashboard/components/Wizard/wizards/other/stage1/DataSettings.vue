<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import CollapsibleContent from '@/dashboard/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard/components/Wizard/components/collapsible/CollapsibleTitle.vue'

const { _t } = usei18n()

interface Props {
  label: TranslatedString
}

defineProps<Props>()

const displayDataSettings = ref<boolean>(true)
</script>

<template>
  <div>
    <CollapsibleTitle
      :title="_t('Data settings')"
      :open="displayDataSettings"
      @toggle-open="displayDataSettings = !displayDataSettings"
    />
    <CollapsibleContent :open="displayDataSettings">
      <TableForm>
        <TableFormRow>
          <FieldDescription>{{ label }}</FieldDescription>
          <FieldComponent>
            <slot />
          </FieldComponent>
        </TableFormRow>
      </TableForm>
    </CollapsibleContent>
  </div>
</template>
