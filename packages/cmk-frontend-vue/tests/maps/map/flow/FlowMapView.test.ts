/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { FakeResizeObserver, useFakeResizeObserver } from 'cmk-ui-library/vitest.resize-observer'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import type { CommandVerb } from '@/maps/api/session'
import FlowMapView from '@/maps/map/flow/FlowMapView.vue'
import type { MapElement, TopologyNode } from '@/maps/types/api'
import { newMapView } from '@/maps/utils/model'

import { aMap, aTopologyNode } from '../../support/fixtures'
import {
  aSession,
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
  checkmkUrl: null as string | null,
  filterNeedle: ''
}

function openFlowMap(
  services: ReturnType<typeof fakeMapsServices>,
  config = baseProps.config,
  topology = sampleTopology()
) {
  services.maps.currentMap.value = config
  services.states.topology.value = topology
  services.states.topologyReady.value = true
}

function renderWithTopology(topology = sampleTopology(), props = baseProps) {
  const services = fakeMapsServices()
  openFlowMap(services, props.config, topology)
  const { global: provided } = provideServices(services)
  return render(FlowMapView, { props, global: { ...provided, stubs } })
}

/** The same map, opened by an operator with the given command permissions. */
async function renderAsCommander(commands: CommandVerb[] = BULK_COMMANDS) {
  const services = fakeMapsServices({}, aSession({ capabilities: fullCapabilities({ commands }) }))
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
  useFakeResizeObserver(FakeResizeObserver)

  beforeEach(() => {
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
  })

  afterEach(() => {
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

  it('pulses a host in trouble where it is drawn', async () => {
    const { container, unmount } = renderWithTopology()
    await waitForNodes()

    const pulses = [...container.querySelectorAll<HTMLElement>('.maps-flow-canvas__pulse')]
    expect(pulses.map((pulse) => pulse.dataset['nodeId'])).toEqual(['db-01'])
    const node = screen.getByRole('button', { name: 'db-01, Down' })
    const [x, y] = (node.getAttribute('transform') ?? '').match(/-?[\d.]+/g)!.map(Number)
    expect(pulses[0]!.style.transform).toBe(`translate(${x}px, ${y}px)`)

    unmount()
  })

  it('counts the service problems of a host down once, as the host down', async () => {
    const topology = sampleTopology()
    topology[2]!.services_summary = { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 }
    const { emitted, unmount } = renderWithTopology(topology)
    await waitForNodes()

    expect(emitted('update:problems')!.at(-1)).toEqual([
      { down: 1, unreachable: 0, critical: 1, warning: 0, unknown: 0, hostsWithProblems: 1 }
    ])

    unmount()
  })

  it('draws the parent tree as links, from the site to the top of its tree', async () => {
    const { container, unmount } = renderWithTopology()
    await waitForNodes()

    // site→core, core→web-01 and core→db-01.
    expect(container.querySelectorAll('path.maps-flow-canvas__link')).toHaveLength(3)

    unmount()
  })

  describe('a group of hosts folded under their parent', () => {
    // More children than a parent shows before folding them; three carry a
    // warning, which opens nothing on its own.
    const wideTopology = (): TopologyNode[] => [
      aTopologyNode({ name: 'core', state: 'UP' }),
      ...Array.from({ length: 30 }, (_, i) =>
        aTopologyNode({
          name: `host-${String(i).padStart(2, '0')}`,
          parents: ['core'],
          state: 'UP',
          services_summary: { ok: 1, warning: i < 3 ? 1 : 0, critical: 0, unknown: 0, pending: 0 },
          unhandled_service_problems: i < 3 ? 1 : 0
        })
      )
    ]

    async function openTheFold() {
      const user = userEvent.setup()
      const view = renderWithTopology(wideTopology())
      await waitForNodes()
      screen.getByRole('button', { name: /^30 hosts below core/ }).focus()
      await user.keyboard('{Enter}')
      return { user, view }
    }

    it('opens to all the hosts it holds, those with problems first', async () => {
      const { view } = await openTheFold()

      await waitFor(() =>
        expect(screen.getByText('Showing 30 hosts below core')).toBeInTheDocument()
      )
      expect(screen.getByRole('button', { name: /^host-03,/ })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /^\d+ hosts below core/ })).toBeNull()
      view.unmount()
    })

    it('names on hover the hosts it holds that need attention, and why', async () => {
      const view = renderWithTopology(wideTopology())
      await waitForNodes()
      const fold = screen.getByRole('button', { name: /^30 hosts below core/ })

      await fireEvent.mouseEnter(fold)

      expect(await screen.findByText('Unhandled problems')).toBeInTheDocument()
      expect(screen.getByText('Hosts below core')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'host-00, WARN services' })).toBeInTheDocument()
      expect(fold.querySelector('title')).toBeNull()
      view.unmount()
    })

    it('links the counts on a site card and a group card into Checkmk views', async () => {
      const view = renderWithTopology(wideTopology(), {
        ...baseProps,
        checkmkUrl: 'http://h/SITE/check_mk/'
      })
      await waitForNodes()
      const viewLinks = async (): Promise<string[]> => {
        const card = (await screen.findByText(/^(Site|Hosts below core)$/)).closest(
          '.maps-hover-card'
        )!
        // The view's own query sits encoded in the start_url of the link.
        return [...card.querySelectorAll('a[href]')].map((link) =>
          decodeURIComponent(decodeURIComponent(link.getAttribute('href')!))
        )
      }

      await fireEvent.mouseEnter(view.container.querySelector('g.maps-flow-canvas__node--site')!)
      const siteLinks = await viewLinks()
      await fireEvent.mouseLeave(view.container.querySelector('g.maps-flow-canvas__node--site')!)
      await waitFor(() => expect(screen.queryByText('Site')).toBeNull())
      await fireEvent.mouseEnter(screen.getByRole('button', { name: /^30 hosts below core/ }))
      const groupLinks = await viewLinks()

      expect(siteLinks).toEqual(
        expect.arrayContaining([
          expect.stringContaining('_active=hoststate;site'),
          expect.stringContaining('_active=svcstate;site')
        ])
      )
      expect(groupLinks).toEqual(
        expect.arrayContaining([
          expect.stringContaining('_active=hoststate;hostregex'),
          expect.stringContaining('host_regex=^(host-00|')
        ])
      )
      view.unmount()
    })

    it('counts on hover the hosts of a site and their services', async () => {
      const view = renderWithTopology(wideTopology())
      await waitForNodes()

      const site = view.container.querySelector('g.maps-flow-canvas__node--site')!

      await fireEvent.mouseEnter(site)

      const card = (await screen.findByText('Site')).closest('.maps-hover-card')!
      expect(card).toHaveTextContent('UP: 31')
      expect(card).toHaveTextContent('WARN: 3')
      expect(site.querySelector('title')).toBeNull()
      view.unmount()
    })

    it('names the hosts a site gathers by the site they are below', async () => {
      const view = renderWithTopology([
        ...wideTopology(),
        ...Array.from({ length: 10 }, (_, i) => aTopologyNode({ name: `top-${i}`, state: 'UP' }))
      ])
      await waitForNodes()

      expect(screen.getByRole('button', { name: /^\d+ hosts below site / })).toBeInTheDocument()
      view.unmount()
    })

    it('keeps its card open while the pointer moves onto it', async () => {
      const view = renderWithTopology(wideTopology())
      await waitForNodes()
      const fold = screen.getByRole('button', { name: /^30 hosts below core/ })
      await fireEvent.mouseEnter(fold)
      const card = (await screen.findByText('Unhandled problems')).closest('.maps-hover-card')!

      await fireEvent.mouseLeave(fold)
      await fireEvent.mouseEnter(card)
      await new Promise((resolve) => setTimeout(resolve, 400))

      expect(screen.getByText('Unhandled problems')).toBeInTheDocument()
      await fireEvent.mouseLeave(card)
      await waitFor(() => expect(screen.queryByText('Unhandled problems')).toBeNull())
      view.unmount()
    })

    it('opens the slide-in of a host its card names', async () => {
      const view = renderWithTopology(wideTopology())
      await waitForNodes()
      await fireEvent.mouseEnter(screen.getByRole('button', { name: /^30 hosts below core/ }))

      await fireEvent.click(await screen.findByRole('button', { name: 'host-00, WARN services' }))

      await waitFor(() =>
        expect(view.emitted('drawer-object')?.at(-1)).toEqual([
          expect.objectContaining({ type: 'host', host_name: 'host-00' })
        ])
      )
      expect(screen.queryByText('Unhandled problems')).toBeNull()
      view.unmount()
    })

    it('draws a host its card names on the map when it is picked', async () => {
      const view = renderWithTopology(wideTopology())
      await waitForNodes()
      await fireEvent.mouseEnter(screen.getByRole('button', { name: /^30 hosts below core/ }))

      await fireEvent.click(await screen.findByRole('button', { name: 'host-00, WARN services' }))

      expect(await screen.findByRole('button', { name: /^host-00,/ })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /^29 hosts below core/ })).toBeInTheDocument()
      view.unmount()
    })

    it('returns the view to where it was once the picked host is closed', async () => {
      const services = fakeMapsServices()
      openFlowMap(services, baseProps.config, wideTopology())
      const { global: provided } = provideServices(services)
      const closableDrawer = defineComponent({
        emits: ['close'],
        setup:
          (_, { emit }) =>
          () =>
            h('button', { onClick: () => emit('close') }, 'Close')
      })
      const view = render(FlowMapView, {
        props: baseProps,
        global: { ...provided, stubs: { ...stubs, DetailDrawer: closableDrawer } }
      })
      await waitForNodes()
      const layer = view.container.querySelector('g.maps-flow-canvas__zoom-layer')!
      await waitFor(() => expect(layer.getAttribute('transform')).toBeTruthy())
      await new Promise((resolve) => setTimeout(resolve, 600))
      const before = layer.getAttribute('transform')
      await fireEvent.mouseEnter(screen.getByRole('button', { name: /^30 hosts below core/ }))
      await fireEvent.click(await screen.findByRole('button', { name: 'host-00, WARN services' }))
      await waitFor(() => expect(layer.getAttribute('transform')).not.toBe(before))

      await fireEvent.click(screen.getByRole('button', { name: 'Close' }))

      await waitFor(() => expect(layer.getAttribute('transform')).toBe(before), { timeout: 3000 })
      view.unmount()
    })

    it('returns the view to where it was once the search is cleared', async () => {
      const view = renderWithTopology(wideTopology())
      await waitForNodes()
      const layer = view.container.querySelector('g.maps-flow-canvas__zoom-layer')!
      await waitFor(() => expect(layer.getAttribute('transform')).toBeTruthy())
      await new Promise((resolve) => setTimeout(resolve, 600))
      const before = layer.getAttribute('transform')
      await view.rerender({ filterNeedle: 'host-17' })
      await waitFor(() => expect(layer.getAttribute('transform')).not.toBe(before), {
        timeout: 3000
      })

      await view.rerender({ filterNeedle: '' })

      await waitFor(() => expect(layer.getAttribute('transform')).toBe(before), { timeout: 3000 })
      view.unmount()
    })

    it('hands keyboard focus to the button that folds the group back', async () => {
      const { view } = await openTheFold()

      await waitFor(() =>
        expect(document.activeElement).toBe(
          screen.getByRole('button', { name: 'Collapse the hosts below core' })
        )
      )
      view.unmount()
    })

    it('folds the group back and returns focus to the fold', async () => {
      const { user, view } = await openTheFold()
      await waitFor(() =>
        expect(document.activeElement).toBe(
          screen.getByRole('button', { name: 'Collapse the hosts below core' })
        )
      )

      await user.keyboard('{Enter}')

      await waitFor(() =>
        expect(screen.getByText('Collapsed the hosts below core')).toBeInTheDocument()
      )
      expect(screen.queryByRole('button', { name: /^host-00,/ })).toBeNull()
      expect(document.activeElement).toBe(
        screen.getByRole('button', { name: /^30 hosts below core/ })
      )
      view.unmount()
    })
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
      aSession({ capabilities: fullCapabilities({ commands: BULK_COMMANDS }) })
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
    vi.mocked(services.apis.mapStates.fetchTopology).mockRejectedValue(new Error('daemon gone'))
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

  it('polls the topology of the map it shows once the stream is lost', async () => {
    const services = fakeMapsServices()
    openFlowMap(services)
    const { unmount } = render(FlowMapView, {
      props: baseProps,
      global: { ...provideServices(services).global, stubs }
    })
    await waitForNodes()

    services.states.streamAvailable.value = false

    await waitFor(() =>
      expect(services.apis.mapStates.fetchTopology).toHaveBeenCalledWith(baseProps.config.name)
    )

    unmount()
  })

  it('asks for the topology again once an edit was handed over without the stream', async () => {
    const services = fakeMapsServices()
    openFlowMap(services)
    const { unmount } = render(FlowMapView, {
      props: baseProps,
      global: { ...provideServices(services).global, stubs }
    })
    await waitForNodes()
    services.states.streamAvailable.value = false
    await waitFor(() => expect(services.apis.mapStates.fetchTopology).toHaveBeenCalled())
    const asked = vi.mocked(services.apis.mapStates.fetchTopology).mock.calls.length

    services.states.handedOver.value++

    await waitFor(() =>
      expect(vi.mocked(services.apis.mapStates.fetchTopology).mock.calls.length).toBe(asked + 1)
    )

    unmount()
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
