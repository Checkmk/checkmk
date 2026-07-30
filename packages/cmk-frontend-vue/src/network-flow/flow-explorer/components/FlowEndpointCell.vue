<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'
import { autonomousSystemSlideInKey, hostSlideInKey } from '@/network-flow/slide-ins/injectionKeys'

const props = defineProps<{
  columnId: string
  address: string
  port: number
  /** Autonomous system of the address; 0 means unresolved and is not shown. */
  asn: number
}>()

// Port 0 is what the flow carries for protocols without ports (ICMP), not a real
// port, so it is left off rather than rendered as ":0".
const endpoint = computed(() =>
  props.port === 0 ? props.address : `${props.address}:${props.port}`
)
const asnLabel = computed(() => (props.asn === 0 ? null : `AS${props.asn}`))

const { _t } = usei18n()

// Injected rather than emitted: the panels are owned by the page, and a cell
// should not have to thread an event up through the table and the row.
const openHostSlideIn = inject(hostSlideInKey, null)
const openAutonomousSystemSlideIn = inject(autonomousSystemSlideInKey, null)

// Without an opener the chip is a plain div, so it must not advertise an action
// it cannot perform either.
const asnTitle = computed(() =>
  openAutonomousSystemSlideIn === null || asnLabel.value === null
    ? {}
    : { title: _t('Show details of %{asn}', { asn: asnLabel.value }) }
)
</script>

<template>
  <BaseCell class="network-flow-flow-endpoint-cell" :column-id="columnId" no-wrap>
    <!-- One row: the endpoint and its autonomous system belong together, and the
         chip is a block element that would otherwise drop onto its own line. -->
    <span class="network-flow-flow-endpoint-cell__content">
      <!-- The title stays on the value: the cell ellipsises, so hovering is how a
           truncated address gets read. The action goes to the accessible name,
           which keeps the visible text inside it so the control still satisfies
           "label in name". -->
      <button
        v-if="openHostSlideIn"
        type="button"
        class="network-flow-flow-endpoint-cell__endpoint network-flow-flow-endpoint-cell__link"
        :title="endpoint"
        :aria-label="_t('Show details of %{endpoint}', { endpoint })"
        @click="openHostSlideIn(address)"
      >
        {{ endpoint }}
      </button>
      <span v-else class="network-flow-flow-endpoint-cell__endpoint" :title="endpoint">{{
        endpoint
      }}</span>
      <CmkChip
        v-if="asnLabel"
        class="network-flow-flow-endpoint-cell__asn"
        size="small"
        variant="outline"
        color="info"
        :as-div="!openAutonomousSystemSlideIn"
        v-bind="asnTitle"
        @click="openAutonomousSystemSlideIn?.(asn)"
      >
        {{ asnLabel }}
      </CmkChip>
    </span>
  </BaseCell>
</template>

<style scoped>
.network-flow-flow-endpoint-cell__content {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  min-width: 0;
}

.network-flow-flow-endpoint-cell__endpoint {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Styled as a link although it is a button: it opens a panel rather than
   navigating, so a button is the honest element. */
.network-flow-flow-endpoint-cell__link {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  text-decoration: underline;
  cursor: pointer;

  &:hover {
    color: var(--color-corporate-green-50);
  }

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }
}

.network-flow-flow-endpoint-cell__asn {
  margin-left: var(--dimension-3);
  flex: 0 0 auto;
}
</style>
