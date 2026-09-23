/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import type { CommandVerb } from '@/maps/api/ticket'
import FlowMapView from '@/maps/map/flow/FlowMapView.vue'
import type { MapElement, TopologyNode } from '@/maps/types/api'
import { newMapView } from '@/maps/utils/model'

import { aMap, aTopologyNode } from '../../support/fixtures'
import {
  aTicket,
  fakeMapsServices,
  fullCapabilities,
  provideServices
} from '../../support/services'

/** What an operator allowed to command a whole selection can do with it. */
const BULK_COMMANDS: CommandVerb[] = ['acknowledge', 'schedule_downtime', 'force_check']

// Hierarchical 3-host topology: core is the root, web-01/db-01 hang off it.
// core carries a services_summary so the donut layout renders ring segments.
const sampleTopology = (): TopologyNode[] => [
  aTopologyNode({
    name: 'core',
    state: 'UP',
    output: 'PING OK',
    services_summary: { ok: 3, warning: 0, critical: 1, unknown: 0, pending: 0 }
  }),
  aTopologyNode({ name: 'web-01', parents: ['core'], state: 'UP', output: 'PING OK' }),
  aTopologyNode({ name: 'db-01', parents: ['core'], state: 'DOWN', output: 'PING CRITICAL' })
]

// The surfaces a node opens are not under test here; stubbing them keeps these
// cases on the view's own d3 render pipeline and its interaction contract.
const stubs = {
  MapSearch: true,
  MapZoomControls: true,
  MapZoomResetPill: true,
  ContextMenu: true,
  DetailDrawer: true,
  HoverMenu: true
}

// The map's own view settings — which services are on show, the problems
// filter — are part of the map, so they are read from the store rather than
// passed in. Which means a case has to open the map, as the page does.
function flowMap() {
  const view = newMapView('flow')
  if (view.type === 'flow') {
    view.service_layout = 'donut'
  }
  return aMap({ name: 'test', connection_id: 'test', view })
}

const baseProps = {
  config: flowMap(),
  error: null,
  canEdit: true,
  kiosk: false,
  preview: false,
  checkmkUrl: null,
  filterNeedle: ''
}

function openFlowMap(services: ReturnType<typeof fakeMapsServices>, config = baseProps.config) {
  services.maps.currentMap.value = config
  services.states.topology.value = sampleTopology()
  services.states.topologyReady.value = true
}

function renderWithTopology() {
  const services = fakeMapsServices()
  openFlowMap(services)
  const { global: provided } = provideServices(services)
  return render(FlowMapView, { props: baseProps, global: { ...provided, stubs } })
}

/** The same map, opened by an operator with the given command permissions. */
async function renderAsCommander(commands: CommandVerb[] = BULK_COMMANDS) {
  const services = fakeMapsServices({}, aTicket({ capabilities: fullCapabilities({ commands }) }))
  await services.auth.init()
  openFlowMap(services)
  const { global: provided } = provideServices(services)
  return render(FlowMapView, { props: baseProps, global: { ...provided, stubs } })
}

/** Shift-clicking two hosts, which is how a selection is built by hand. */
async function pickTwoNodes() {
  // Only the click is dispatched: a full pointer press would also start
  // d3-drag, which reads a view off the event that jsdom does not give it.
  await fireEvent.click(screen.getByRole('button', { name: 'db-01, Down' }), { shiftKey: true })
  await fireEvent.click(screen.getByRole('button', { name: 'web-01, Up' }), { shiftKey: true })
}

// The d3 pipeline renders asynchronously after mount; wait for the host nodes
// (their accessible names carry the live state) before asserting structure.
async function waitForNodes() {
  await waitFor(() => expect(screen.getByRole('button', { name: 'core, Up' })).toBeInTheDocument())
}

describe('FlowMapView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // jsdom has no layout: getBBox / getBoundingClientRect on SVG elements
    // would throw or return zeros. d3 itself is pure JS and runs as-is.
    Object.defineProperty(SVGElement.prototype, 'getBBox', {
      configurable: true,
      value: () => ({ x: 0, y: 0, width: 10, height: 10 })
    })
    // d3-zoom's defaultExtent reads svg.width/height.baseVal, which jsdom's
    // SVGSVGElement does not implement.
    for (const dim of ['width', 'height'] as const) {
      Object.defineProperty(SVGSVGElement.prototype, dim, {
        configurable: true,
        get: () => ({ baseVal: { value: dim === 'width' ? 900 : 600 } })
      })
    }
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    Reflect.deleteProperty(SVGElement.prototype, 'getBBox')
    Reflect.deleteProperty(SVGSVGElement.prototype, 'width')
    Reflect.deleteProperty(SVGSVGElement.prototype, 'height')
  })

  it('renders one d3 node per host plus the synthetic site root', async () => {
    const { container, unmount } = renderWithTopology()
    await waitForNodes()

    // Hosts carry their live state in the accessible name.
    expect(screen.getByRole('button', { name: 'web-01, Up' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'db-01, Down' })).toBeInTheDocument()

    // Geometry: the node-kind CSS classes and label texts of the d3 structure
    // have no further accessible representation — container-scoped queries.
    const svg = container.querySelector('svg.maps-flow-canvas__svg')
    expect(svg).not.toBeNull()
    expect(svg!.querySelectorAll('g.maps-flow-canvas__node--host')).toHaveLength(3)
    expect(svg!.querySelectorAll('g.maps-flow-canvas__node--site')).toHaveLength(1)

    const labels = [...svg!.querySelectorAll('text.maps-flow-canvas__label')].map(
      (text) => text.textContent
    )
    expect(labels).toEqual(expect.arrayContaining(['core', 'web-01', 'db-01', 'test']))

    unmount()
  })

  it('draws parent-child links and site links as lines', async () => {
    const { container, unmount } = renderWithTopology()
    await waitForNodes()

    // 2 parent→child links (core→web-01, core→db-01) + 1 site→root link.
    expect(container.querySelectorAll('line.maps-flow-canvas__link')).toHaveLength(3)

    unmount()
  })

  it('renders donut ring segments from the services_summary in donut layout', async () => {
    const { container, unmount } = renderWithTopology()
    await waitForNodes()

    // core: ok=3 + critical=1 → two arcs; the other hosts have no summary.
    expect(container.querySelectorAll('g.maps-flow-canvas__donut path')).toHaveLength(2)

    unmount()
  })

  it('fires the click contract via keyboard: focus a node, press Enter', async () => {
    // Pins the accessibility path: flow nodes are reachable and activatable
    // without a pointer. Enter mirrors a plain click and opens the slide-in,
    // observable at the component boundary as the drawer-object emit.
    const user = userEvent.setup()
    const services = fakeMapsServices()
    openFlowMap(services)
    const opened = ref<MapElement | null>(null)
    render(
      defineComponent({
        components: { FlowMapView },
        setup() {
          const onDrawerObject = (object: MapElement | null) => {
            opened.value = object
          }
          return { baseProps, onDrawerObject }
        },
        template: `<FlowMapView v-bind="baseProps" @drawer-object="onDrawerObject" />`
      }),
      { global: { ...provideServices(services).global, stubs } }
    )
    await waitForNodes()

    const node = screen.getByRole('button', { name: 'db-01, Down' })
    node.focus()
    await user.keyboard('{Enter}')

    await waitFor(() => expect(opened.value).toMatchObject({ type: 'host', host_name: 'db-01' }))
  })

  it('offers the group commands once several nodes are picked', async () => {
    // Shift-click builds the selection, and the bar counts what it applies to —
    // the commands behind it go out to every one of them, not just the last.
    const { unmount } = await renderAsCommander()
    await waitForNodes()

    await pickTwoNodes()

    await waitFor(() => expect(screen.getByText('2 selected')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Acknowledge…' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Schedule downtime…' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Force check' })).toBeInTheDocument()

    unmount()
  })

  it('acknowledges only the picked hosts that have a problem', async () => {
    // Checkmk refuses to acknowledge a host that is UP, so it is left out and
    // the dialog says so, rather than the command failing for it.
    const { unmount } = await renderAsCommander()
    await waitForNodes()
    await pickTwoNodes()

    await fireEvent.click(await screen.findByRole('button', { name: 'Acknowledge…' }))

    expect(await screen.findByText('1 without a problem left out')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Acknowledge 1' })).toBeInTheDocument()

    unmount()
  })

  it('offers a selection no command the operator is not allowed to send', async () => {
    // A command sent to a whole selection needs the same permission as one sent
    // to a single object: the bar is not a way around it.
    const { unmount } = await renderAsCommander(['acknowledge'])
    await waitForNodes()

    await pickTwoNodes()

    await waitFor(() => expect(screen.getByText('2 selected')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Acknowledge…' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Schedule downtime…' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Force check' })).not.toBeInTheDocument()

    unmount()
  })

  it('drops the selection when the view is handed a different map', async () => {
    // One view draws every flow map in turn. A selection assembled on one of
    // them would otherwise still be behind the command bar on the next, and an
    // acknowledgement would go to the hosts of the map the operator just left.
    const { rerender, unmount } = await renderAsCommander()
    await waitForNodes()
    await pickTwoNodes()
    await waitFor(() => expect(screen.getByText('2 selected')).toBeInTheDocument())

    await rerender({
      ...baseProps,
      config: aMap({ name: 'other', connection_id: 'other', view: flowMap().view })
    })

    await waitForNodes()
    expect(screen.queryByText('2 selected')).not.toBeInTheDocument()

    unmount()
  })

  it('shows no command bar at all to an operator allowed to send none', async () => {
    const { unmount } = await renderAsCommander([])
    await waitForNodes()

    await pickTwoNodes()

    // The selection itself still happens — it is what a lasso and a hover card
    // read — but it leads to nothing that would send a command.
    await waitFor(() => expect(screen.queryByText('2 selected')).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Acknowledge…' })).not.toBeInTheDocument()

    unmount()
  })

  it('sends no command from a kiosk, whatever the operator may otherwise do', async () => {
    const services = fakeMapsServices(
      {},
      aTicket({ capabilities: fullCapabilities({ commands: BULK_COMMANDS }) })
    )
    await services.auth.init()
    openFlowMap(services)
    const { global: provided } = provideServices(services)
    const { unmount } = render(FlowMapView, {
      props: { ...baseProps, kiosk: true },
      global: { ...provided, stubs }
    })
    await waitForNodes()

    await pickTwoNodes()

    await waitFor(() => expect(screen.queryByText('2 selected')).not.toBeInTheDocument())

    unmount()
  })

  it('keeps the drawn topology when a poll for a fresh one fails', async () => {
    // A failed request is usually one missed poll out of many. Replacing the
    // map with an error would cost the arrangement, the zoom and the selection
    // for it, so the last topology stays up and the failure is said over it.
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const services = fakeMapsServices()
    openFlowMap(services)
    vi.mocked(services.apis.connections.fetchTopology).mockRejectedValue(new Error('daemon gone'))
    const { container, unmount } = render(FlowMapView, {
      props: baseProps,
      global: { ...provideServices(services).global, stubs }
    })
    await waitForNodes()

    // Losing the stream is what puts the feed on the polling fallback.
    services.states.streamAvailable.value = false

    await waitFor(() =>
      expect(
        screen.getByText('Topology update failed — showing the last one that arrived')
      ).toBeInTheDocument()
    )
    expect(container.querySelector('svg.maps-flow-canvas__svg')).not.toBeNull()
    expect(screen.getByRole('button', { name: 'core, Up' })).toBeInTheDocument()

    unmount()
    warn.mockRestore()
  })

  it('says so, rather than drawing nothing, when the map has no connection', async () => {
    // A flow map's hosts come from a connection; without one there is nothing
    // to ask, and the view has to say why it is empty.
    const services = fakeMapsServices()
    const config = aMap({ connection_id: '', view: newMapView('flow') })
    services.maps.currentMap.value = config
    const { global: provided } = provideServices(services)
    render(FlowMapView, { props: { ...baseProps, config }, global: { ...provided, stubs } })

    await waitFor(() =>
      expect(screen.getByText('No connection configured for this map.')).toBeInTheDocument()
    )
  })

  it('unmounts cleanly while the force simulation is still settling', async () => {
    const { container, unmount } = renderWithTopology()
    await waitForNodes()

    unmount()
    // Let any stray simulation/zoom rAF or timer callbacks fire — a stopped
    // simulation must not tick (and must not throw) after unmount.
    await new Promise((resolve) => setTimeout(resolve, 60))
    expect(container.querySelector('svg.maps-flow-canvas__svg')).toBeNull()
  })
})
