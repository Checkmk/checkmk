<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkTag, {
  type Colors,
  type Sizes,
  type Variants
} from 'cmk-ui-library/components/CmkTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, inject, nextTick, onMounted, ref, watch } from 'vue'

import { COLUMN_LAYOUT_KEY } from '../MonitoringTableContext'
import BaseCell from './BaseCell.vue'

export interface LabelCellItem {
  text: TranslatedString
  color?: Colors | undefined
  variant?: Variants | undefined
}

export interface LabelCellProps {
  items: LabelCellItem[]
  size?: Sizes | undefined
  columnId?: string | undefined
}

const props = defineProps<LabelCellProps>()

const { _t } = usei18n()

const row = ref<HTMLElement | null>(null)
const expanded = ref(false)
const measuring = ref(true)
const itemEnds = ref<number[]>([])
const overflowReserve = ref(0)
const measuredRowWidth = ref(0)

/**
 * The table already tracks every column's width and shares it, so the row's own width follows from
 * that rather than from a second observer per row - these cells are rendered by a virtualizer that
 * mounts and unmounts them on every scroll tick.
 */
const columns = inject(COLUMN_LAYOUT_KEY, null)
const columnWidth = computed(() =>
  props.columnId ? (columns?.value.get(props.columnId)?.width ?? null) : null
)

/** What the cell's padding takes off the column, captured while measuring. */
const rowInset = ref(0)

const rowWidth = computed(() =>
  columnWidth.value === null ? measuredRowWidth.value : columnWidth.value - rowInset.value
)

/**
 * While measuring, every item plus the overflow button is laid out at its natural width in a
 * single non-wrapping row, so the right edge each item ends at can be read off the DOM. Those
 * edges already include the gaps between the items, and they stay valid until either the items or
 * the column width change.
 *
 * At least one item is always shown: a single item too wide for the column is ellipsised instead.
 */
const fittingCount = computed(() => {
  if (measuring.value || itemEnds.value.length === 0) {
    return props.items.length
  }
  const total = itemEnds.value.length
  for (let count = total; count > 1; count -= 1) {
    const reserve = count < total ? overflowReserve.value : 0
    if (itemEnds.value[count - 1]! + reserve <= rowWidth.value) {
      return count
    }
  }
  return 1
})

const hasOverflow = computed(() => fittingCount.value < props.items.length)
const visibleItems = computed(() =>
  expanded.value || measuring.value ? props.items : props.items.slice(0, fittingCount.value)
)
const hiddenCount = computed(() => props.items.length - fittingCount.value)

/**
 * While measuring nothing is hidden yet, so the button would be sized for "+0" and reserve too
 * little for the "+12" it may end up showing. Measuring the largest count it could ever reach
 * keeps the reserve an upper bound.
 */
const overflowLabel = computed(() =>
  measuring.value ? `+${Math.max(props.items.length - 1, 0)}` : `+${hiddenCount.value}`
)

/**
 * An entry too wide for the cell is ellipsised to what is left once the "+X" button has its room,
 * so the button never ends up clipped by the row.
 */
const tagMaxWidth = computed(() =>
  !measuring.value && hasOverflow.value && !expanded.value
    ? `calc(100% - ${overflowReserve.value}px)`
    : '100%'
)

async function measure(): Promise<void> {
  measuring.value = true
  await nextTick()
  const element = row.value
  if (!element) {
    return
  }
  const rowLeft = element.getBoundingClientRect().left
  const items = Array.from(element.querySelectorAll<HTMLElement>('[data-label-cell-item]')).map(
    (node) => node.getBoundingClientRect()
  )
  itemEnds.value = items.map((rect) => rect.right - rowLeft)
  const button = element.querySelector<HTMLElement>('[data-label-cell-overflow]')
  const lastItem = items[items.length - 1]
  overflowReserve.value =
    button && lastItem
      ? button.getBoundingClientRect().right - lastItem.right
      : (button?.getBoundingClientRect().width ?? 0)
  measuredRowWidth.value = element.clientWidth
  rowInset.value = columnWidth.value === null ? 0 : columnWidth.value - element.clientWidth
  measuring.value = false
}

onMounted(() => {
  void measure()
})

// Keyed on the entries themselves: a poll that hands the row an equal-but-new array must not
// trigger another measuring pass.
watch(
  () => props.items.map((item) => item.text).join('\u0000'),
  () => {
    expanded.value = false
    void measure()
  }
)
</script>

<template>
  <BaseCell class="monitoring-label-cell" :column-id="columnId">
    <template #default>
      <div
        ref="row"
        class="monitoring-label-cell__row"
        :class="{
          'monitoring-label-cell__row--measuring': measuring,
          'monitoring-label-cell__row--expanded': expanded && !measuring
        }"
      >
        <CmkTag
          v-for="(item, index) in visibleItems"
          :key="`${index}-${item.text}`"
          data-label-cell-item
          class="monitoring-label-cell__tag"
          :style="{ maxWidth: tagMaxWidth }"
          :title="item.text"
          :size="size"
          :variant="item.variant ?? 'fill'"
          :color="item.color ?? 'default'"
          :content="item.text"
        />
        <CmkButton
          v-if="measuring || (hasOverflow && !expanded)"
          data-label-cell-overflow
          class="monitoring-label-cell__overflow"
          size="small"
          variant="optional"
          :aria-label="_t('Show all %{count} entries', { count: items.length })"
          @click="expanded = true"
        >
          {{ overflowLabel }}
        </CmkButton>
        <CmkButton
          v-if="expanded && !measuring"
          class="monitoring-label-cell__overflow"
          size="small"
          variant="optional"
          @click="expanded = false"
        >
          {{ _t('show less') }}
        </CmkButton>
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-label-cell__row {
  display: flex;
  flex-flow: row nowrap;
  gap: var(--dimension-3);
  align-items: center;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.monitoring-label-cell__row--measuring {
  visibility: hidden;
}

.monitoring-label-cell__row--expanded {
  flex-flow: row wrap;
  overflow: visible;
}

/**
 * The row's gap is the only spacing between entries, so the tag's own horizontal margin is
 * dropped. Its line height comes from the cell otherwise, which would keep every tag the same
 * height no matter its size.
 */
.monitoring-label-cell__tag {
  flex: 0 1 auto;
  margin: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  line-height: normal;
}

.monitoring-label-cell__overflow {
  flex: 0 0 auto;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-label-cell :deep(.monitoring-base-cell__plain) {
  min-width: 0;
  width: 100%;
}
</style>
