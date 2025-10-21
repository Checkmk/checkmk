<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHelpText from '@/components/CmkHelpText.vue'

import { DashboardLayout } from '@/dashboard-wip/types/dashboard'

import RadioButton from '../RadioButton.vue'
import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'

const { _t } = usei18n()

interface DashboardLayoutSelectorProps {
  availableLayouts: DashboardLayout[]
}

defineProps<DashboardLayoutSelectorProps>()

const dashboardLayout = defineModel<DashboardLayout>('dashboardLayout', { required: true })

const _updateDashboardLayout = (newLayout: string) => {
  dashboardLayout.value =
    newLayout === DashboardLayout.RELATIVE_GRID
      ? DashboardLayout.RELATIVE_GRID
      : DashboardLayout.RESPONSIVE_GRID
}
</script>

<template>
  <TableForm>
    <TableFormRow>
      <FieldDescription>
        {{ _t('Dashboard layout') }}
        <CmkHelpText
          :help="
            _t(
              'You can choose between a fixed layout or a responsive, scrollable grid layout. By default, the responsive grid layout is selected.'
            )
          "
        />
      </FieldDescription>
      <FieldComponent>
        <div class="db-general-properties__item">
          <RadioButton
            v-if="availableLayouts.includes(DashboardLayout.RESPONSIVE_GRID)"
            :model-value="dashboardLayout"
            :value="DashboardLayout.RESPONSIVE_GRID"
            :label="_t('Responsive')"
            @update:model-value="_updateDashboardLayout"
          />
        </div>
        <div class="db-general-properties__item">
          <RadioButton
            v-if="availableLayouts.includes(DashboardLayout.RELATIVE_GRID)"
            :model-value="dashboardLayout"
            :value="DashboardLayout.RELATIVE_GRID"
            :label="_t('Legacy')"
            @update:model-value="_updateDashboardLayout"
          />
        </div>
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
