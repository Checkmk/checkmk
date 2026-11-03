<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import { getIconPath } from 'cmk-ui-library/components/CmkIcon/utils'
import CmkPointerTooltip, {
  type CmkPointerTooltipPointer
} from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useTheme } from 'cmk-ui-library/lib/useTheme'
import { computed, ref, useTemplateRef, watch } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import { contextualLinkCount } from '@/dashboard/lib/contextualLinkUrl'
import type {
  SiteOverviewContent,
  SiteOverviewSites,
  VisualContext
} from '@/dashboard/types/widget'

import FigureTooltip, { type FigureTooltipContent } from './lib/FigureTooltip.vue'
import StateRingsHexagon from './lib/StateRingsHexagon.vue'
import { byKeyboard } from './lib/byKeyboard'
import { describeFigureTooltip } from './lib/describeFigureTooltip'
import { HEXAGON_MAX_BOX_WIDTH, STATE_HEXAGON_STYLE, hexagonGrid, hexagonPath } from './lib/hexagon'

const props = defineProps<{
  value: SiteOverviewSites
  width: number
  height: number
  hexagonSize: SiteOverviewContent['hexagon_size']
  filters: VisualContext
}>()

const { _t, _tnp } = usei18n()
const { theme } = useTheme()

type SiteElement = SiteOverviewSites['sites'][number]
type SitePart = Extract<SiteElement, { status: 'online' }>['parts'][number]

const SITE_PART_TEXT: Record<SitePart['category'], (count: number) => string> = {
  critical: (count) =>
    _tnp(
      'site overview',
      'host is down or has critical services',
      'hosts are down or have critical services',
      count
    ),
  unknown: (count) =>
    _tnp(
      'site overview',
      'host is unreachable or has unknown services',
      'hosts are unreachable or have unknown services',
      count
    ),
  warning: (count) =>
    _tnp(
      'site overview',
      'host is UP but has services in WARNING state',
      'hosts are UP but have services in WARNING state',
      count
    ),
  downtime: (count) =>
    _tnp(
      'site overview',
      'host is in scheduled downtime',
      'hosts are in scheduled downtime',
      count
    ),
  ok: (count) =>
    _tnp(
      'site overview',
      'host is up and has no service problems',
      'hosts are up and have no service problems',
      count
    )
}

type OfflineStatus = Exclude<SiteElement['status'], 'online'>

const OFFLINE_SITE: Record<OfflineStatus, { text: string; icon: SimpleIcons }> = {
  disabled: { text: _t('The connection to this site has been disabled.'), icon: 'site-disabled' },
  down: { text: _t('This site is currently down.'), icon: 'site-down' },
  unreach: { text: _t('This site is currently not reachable.'), icon: 'site-unreach' },
  dead: { text: _t('This site is not responding.'), icon: 'site-dead' },
  waiting: {
    text: _t('The status of this site has not yet been determined.'),
    icon: 'site-waiting'
  },
  missing: { text: _t('This site does not exist.'), icon: 'site-missing' },
  unknown: { text: _t('The status of this site could not be determined.'), icon: 'site-missing' }
}

const FIGURE_LABEL = _t('Site overview')

function total(site: SiteElement): number {
  return site.status === 'online' ? site.parts.reduce((sum, part) => sum + part.count, 0) : 0
}

const shapes = computed(() => {
  const grid = hexagonGrid(props.value.sites.length, props.width, props.height, {
    layout: 'sites',
    maxBoxWidth: HEXAGON_MAX_BOX_WIDTH[props.hexagonSize]
  })
  if (grid === null) {
    return []
  }
  const largest = Math.max(0, ...props.value.sites.map(total))
  return props.value.sites.map((site, index) => {
    const center = grid.centers[index]!
    const base = {
      site,
      transform: `translate(${center.x}, ${center.y})`,
      hitPath: hexagonPath(grid.radius),
      label:
        grid.labelHeight === null
          ? null
          : { y: grid.radius + 4, width: grid.boxWidth, height: grid.labelHeight }
    }
    if (site.status !== 'online') {
      return { ...base, rings: null, iconPath: hexagonPath(grid.radius * 0.5) }
    }
    const scale = largest === 0 ? 0.5 : Math.max(0.5, Math.pow(total(site) / largest, 0.3))
    return {
      ...base,
      iconPath: null,
      rings: { parts: [...site.parts].reverse(), radius: grid.radius * scale }
    }
  })
})

const hovered = ref<{ site: SiteElement; pointer: CmkPointerTooltipPointer } | null>(null)

// While a site's link menu is open, its tooltip stays and the menu opens right below it.
const menuOpenFor = ref<string | null>(null)
const tooltipElement = useTemplateRef<InstanceType<typeof CmkPointerTooltip>>('tooltipElement')

watch(menuOpenFor, (site) => {
  if (site === null) {
    hovered.value = null
  }
})

function hover(site: SiteElement, event: PointerEvent): void {
  if (menuOpenFor.value === null) {
    hovered.value = { site, pointer: { clientX: event.clientX, clientY: event.clientY } }
  }
}

function leave(): void {
  if (menuOpenFor.value === null) {
    hovered.value = null
  }
}

function focusSite(site: SiteElement, event: FocusEvent): void {
  if (
    menuOpenFor.value !== null ||
    !byKeyboard(event) ||
    !(event.currentTarget instanceof Element)
  ) {
    return
  }
  const bounds = event.currentTarget.getBoundingClientRect()
  hovered.value = {
    site,
    pointer: { clientX: bounds.left + bounds.width / 2, clientY: bounds.top + bounds.height / 2 }
  }
}

function opensMenu(site: SiteElement | undefined): boolean {
  return (
    site?.status === 'online' && contextualLinkCount(props.value.links, site.link_properties) > 1
  )
}

const several = computed(() => opensMenu(hovered.value?.site))

// A refresh can take the menu away with its site, without the menu reporting that it closed.
watch(
  () => opensMenu(props.value.sites.find((site) => site.site_id === menuOpenFor.value)),
  (menu) => {
    if (!menu) {
      menuOpenFor.value = null
    }
  }
)

function tooltipOf(site: SiteElement): FigureTooltipContent {
  if (site.status !== 'online') {
    return { title: site.alias, state: OFFLINE_SITE[site.status].text, rows: [] }
  }
  const count = total(site)
  return {
    title: site.alias,
    state: null,
    rows: [
      ...site.parts.map((part) => ({
        key: part.category,
        count: part.count,
        color: STATE_HEXAGON_STYLE[part.category].color,
        text: SITE_PART_TEXT[part.category](part.count)
      })),
      {
        key: 'total',
        count,
        color: 'transparent',
        text: _tnp('site overview', 'host in total', 'hosts in total', count)
      }
    ]
  }
}

const tooltip = computed(() => (hovered.value ? tooltipOf(hovered.value.site) : null))

function siteName(site: SiteElement): string {
  return `${site.alias}, ${describeFigureTooltip(tooltipOf(site))}`
}
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-site-overview-sites-figure"
    :aria-label="FIGURE_LABEL"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <g
      v-for="shape in shapes"
      :key="shape.site.site_id"
      class="db-cmk-site-overview-sites-figure__site"
      :transform="shape.transform"
      @pointermove="hover(shape.site, $event)"
      @pointerleave="leave"
      @focusin="focusSite(shape.site, $event)"
      @focusout="leave"
      @keydown.escape="leave"
    >
      <ContextualLinkTrigger
        v-if="shape.site.status === 'online'"
        :open="menuOpenFor === shape.site.site_id"
        :links="value.links"
        :link-properties="shape.site.link_properties"
        :filters="filters"
        :reference="tooltipElement?.element ?? null"
        @update:open="(open: boolean) => (menuOpenFor = open ? shape.site.site_id : null)"
      >
        <g :aria-label="siteName(shape.site)">
          <path :d="shape.hitPath" fill="transparent" />
          <StateRingsHexagon
            v-if="shape.rings"
            :parts="shape.rings.parts"
            :radius="shape.rings.radius"
            :ring-label="null"
          />
        </g>
      </ContextualLinkTrigger>
      <g v-else :aria-label="siteName(shape.site)" role="img" tabindex="0">
        <path :d="shape.hitPath" fill="transparent" />
        <path :d="shape.iconPath ?? ''" class="db-cmk-site-overview-sites-figure__offline" />
        <image
          :href="getIconPath(OFFLINE_SITE[shape.site.status].icon, theme)"
          x="-12"
          y="-12"
          width="24"
          height="24"
        />
      </g>
      <path
        :d="shape.hitPath"
        class="db-cmk-site-overview-sites-figure__highlight"
        pointer-events="none"
      />
      <foreignObject
        v-if="shape.label"
        :x="-shape.label.width / 2"
        :y="shape.label.y"
        :width="shape.label.width"
        :height="shape.label.height + 4"
      >
        <div
          class="db-cmk-site-overview-sites-figure__label"
          :style="{ fontSize: `${shape.label.height}px` }"
        >
          {{ shape.site.alias }}
        </div>
      </foreignObject>
    </g>
  </svg>
  <CmkPointerTooltip ref="tooltipElement" :pointer="hovered?.pointer ?? null" @dismiss="leave">
    <FigureTooltip v-if="tooltip" v-bind="tooltip" :several="several" />
  </CmkPointerTooltip>
</template>

<style scoped>
.db-cmk-site-overview-sites-figure {
  display: block;
}

.db-cmk-site-overview-sites-figure__highlight {
  fill: transparent;
}

.db-cmk-site-overview-sites-figure__site:is(:hover, :has(:focus-visible))
  .db-cmk-site-overview-sites-figure__highlight {
  fill: color-mix(in srgb, var(--font-color) 10%, transparent);
}

.db-cmk-site-overview-sites-figure__offline {
  fill: var(--background-muted);
  stroke: rgb(68 68 68);
  stroke-dasharray: 3, 3;
}

.db-cmk-site-overview-sites-figure__label {
  overflow: hidden;
  color: var(--font-color);
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
