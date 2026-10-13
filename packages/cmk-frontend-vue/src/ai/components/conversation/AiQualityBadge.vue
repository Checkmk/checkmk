<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import CmkProgressCircle, {
  type Colors
} from 'cmk-ui-library/components/progress/CmkProgressCircle.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { QualityLevel } from '@/ai/lib/markdown'

const { _t } = usei18n()

const props = defineProps<{ level: QualityLevel | null }>()

const QUALITY_RING_LABEL = 'AI'

const qualityLevelText = computed<string>(() => {
  switch (props.level) {
    case 'high':
      return _t('High')
    case 'medium':
      return _t('Medium')
    case 'low':
      return _t('Low')
    default:
      return ''
  }
})

const qualityAriaLabel = computed<string>(() => {
  if (!props.level) {
    return ''
  }
  return `${_t('Data quality')}: ${qualityLevelText.value}`
})

const QUALITY_RING_VALUE: Record<QualityLevel, number> = {
  high: 80,
  medium: 50,
  low: 25
}

const QUALITY_CIRCLE_COLOR: Record<QualityLevel, Colors> = {
  high: 'success',
  medium: 'warning',
  low: 'danger'
}

const qualityTooltipOpen = ref<boolean>(false)
</script>

<template>
  <div
    role="img"
    :aria-label="qualityAriaLabel"
    class="ai-quality-badge"
    :class="[
      { 'ai-quality-badge--hidden': !props.level },
      props.level ? `ai-quality-badge--${props.level}` : ''
    ]"
  >
    <span class="ai-quality-badge__label">{{ _t('Data quality') }}</span>
    <CmkTooltipProvider :delay-duration="200">
      <CmkTooltip
        :open="qualityTooltipOpen"
        @update:open="(value: boolean) => (qualityTooltipOpen = value)"
      >
        <CmkTooltipTrigger as-child>
          <button
            type="button"
            :aria-label="_t('Data quality information')"
            class="ai-quality-badge__info-trigger"
          >
            <CmkIcon name="info-circle" size="small" />
          </button>
        </CmkTooltipTrigger>
        <CmkTooltipContent side="top" align="center" variant="content" :avoid-collisions="true">
          <div class="ai-quality-badge__tooltip-content">
            {{
              _t(
                'Indicates completeness and reliability of the data used to generate this answer. High means all key fields are present; Medium that some data might be missing; Low that the data is insufficient or unavailable.'
              )
            }}
          </div>
        </CmkTooltipContent>
      </CmkTooltip>
    </CmkTooltipProvider>
    <span class="ai-quality-badge__colon">:</span>
    <span
      class="ai-quality-badge__ring-badge"
      :class="
        props.level
          ? `ai-quality-badge__ring-badge--${props.level}`
          : 'ai-quality-badge__ring-badge--hidden'
      "
    >
      <CmkProgressCircle
        size="small"
        :value="props.level ? QUALITY_RING_VALUE[props.level] : 0"
        :color="props.level ? QUALITY_CIRCLE_COLOR[props.level] : 'success'"
        :max="100"
      />
      <span class="ai-quality-badge__ring-label">{{ QUALITY_RING_LABEL }}</span>
    </span>
    <span
      class="ai-quality-badge__level-text"
      :class="props.level ? `ai-quality-badge__level-text--${props.level}` : ''"
      >{{ qualityLevelText }}</span
    >
  </div>
</template>

<style scoped>
.ai-quality-badge {
  margin-left: auto;
  align-self: stretch;
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  white-space: nowrap;
}

.ai-quality-badge--hidden {
  visibility: hidden;
}

.ai-quality-badge__label {
  font-size: 12px;
  font-weight: bold;
  opacity: 0.8;
}

.ai-quality-badge__colon {
  font-size: 12px;
  opacity: 0.8;
}

.ai-quality-badge__info-trigger {
  background: none;
  border: none;
  padding: 0;
  display: flex;
  align-items: center;
  margin: 0 calc(-1 * var(--dimension-3));
  cursor: pointer;
}

.ai-quality-badge__tooltip-content {
  max-width: 240px;
  white-space: normal;
  text-align: left;
}

.ai-quality-badge__ring-badge {
  position: relative;
  display: inline-flex;
  cursor: default;
}

.ai-quality-badge__ring-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  color: var(--ai-quality-color);
}

.ai-quality-badge__ring-badge--hidden {
  visibility: hidden;
}

.ai-quality-badge__level-text {
  font-size: 12px;
  font-weight: bold;
  color: var(--ai-quality-color);
  min-width: 5em;
}

.ai-quality-badge--high {
  --ai-quality-color: var(--status-text-color-success-on-tint);
}

.ai-quality-badge--medium {
  --ai-quality-color: var(--status-text-color-warning-strong);
}

.ai-quality-badge--low {
  --ai-quality-color: var(--status-text-color-error-soft);
}
</style>
