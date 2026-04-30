/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, within } from '@testing-library/vue'
import UclCmkBadge from '@ucl/components/basic-elements/CmkBadge/UclCmkBadge.vue'
import UclCmkButton from '@ucl/components/basic-elements/CmkButton/UclCmkButton.vue'
import UclCmkButtonCancel from '@ucl/components/basic-elements/CmkButtonCancel/UclCmkButtonCancel.vue'
import UclCmkButtonSubmit from '@ucl/components/basic-elements/CmkButtonSubmit/UclCmkButtonSubmit.vue'
import UclCmkChip from '@ucl/components/basic-elements/CmkChip/UclCmkChip.vue'
import UclCmkCode from '@ucl/components/basic-elements/CmkCode/UclCmkCode.vue'
import UclCmkColorPicker from '@ucl/components/basic-elements/CmkColorPicker/UclCmkColorPicker.vue'
import UclCmkIconButton from '@ucl/components/basic-elements/CmkIconButton/UclCmkIconButton.vue'
import UclCmkInlineButton from '@ucl/components/basic-elements/CmkInlineButton/UclCmkInlineButton.vue'
import UclCmkSwitch from '@ucl/components/basic-elements/CmkSwitch/UclCmkSwitch.vue'
import UclCmkTag from '@ucl/components/basic-elements/CmkTag/UclCmkTag.vue'
import UclCmkAccordion from '@ucl/components/content-organization/CmkAccordion/UclCmkAccordion.vue'
import UclCmkAccordionStepPanel from '@ucl/components/content-organization/CmkAccordionStepPanel/UclCmkAccordionStepPanel.vue'
import UclCmkCatalogPanel from '@ucl/components/content-organization/CmkCatalogPanel/UclCmkCatalogPanel.vue'
import UclCmkCollapsible from '@ucl/components/content-organization/CmkCollapsible/UclCmkCollapsible.vue'
import UclCmkScrollContainer from '@ucl/components/content-organization/CmkScrollContainer/UclCmkScrollContainer.vue'
import UclCmkSlideIn from '@ucl/components/content-organization/CmkSlideIn/UclCmkSlideIn.vue'
import UclCmkSlideInDialog from '@ucl/components/content-organization/CmkSlideInDialog/UclCmkSlideInDialog.vue'
import UclCmkTabs from '@ucl/components/content-organization/CmkTabs/UclCmkTabs.vue'
import UclCmkWizard from '@ucl/components/content-organization/CmkWizard/UclCmkWizard.vue'
import UclCmkCheckbox from '@ucl/components/form-elements/CmkCheckbox/UclCmkCheckbox.vue'
import UclCmkConfigurationEntityDropdown from '@ucl/components/form-elements/CmkConfigurationEntityDropdown/UclCmkConfigurationEntityDropdown.vue'
import UclCmkDateTimePicker from '@ucl/components/form-elements/CmkDateTimePicker/UclCmkDateTimePicker.vue'
import UclCmkDropdown from '@ucl/components/form-elements/CmkDropdown/UclCmkDropdown.vue'
import UclCmkDualList from '@ucl/components/form-elements/CmkDualList/UclCmkDualList.vue'
import UclCmkInput from '@ucl/components/form-elements/CmkInput/UclCmkInput.vue'
import UclCmkList from '@ucl/components/form-elements/CmkList/UclCmkList.vue'
import UclCmkTimeSpan from '@ucl/components/form-elements/CmkTimeSpan/UclCmkTimeSpan.vue'
import UclCmkToggleButtonGroup from '@ucl/components/form-elements/CmkToggleButtonGroup/UclCmkToggleButtonGroup.vue'
import UclCmkHtml from '@ucl/components/foundation-elements/CmkHtml/UclCmkHtml.vue'
import UclCmkIcon from '@ucl/components/foundation-elements/CmkIcon/UclCmkIcon.vue'
import UclCmkIconEmblem from '@ucl/components/foundation-elements/CmkIcon/UclCmkIconEmblem.vue'
import UclCmkMultitoneIcon from '@ucl/components/foundation-elements/CmkIcon/UclCmkMultitoneIcon.vue'
import UclCmkIndent from '@ucl/components/foundation-elements/CmkIndent/UclCmkIndent.vue'
import UclCmkKeyboardKey from '@ucl/components/foundation-elements/CmkKeyboardKey/UclCmkKeyboardKey.vue'
import UclCmkLabel from '@ucl/components/foundation-elements/CmkLabel/UclCmkLabel.vue'
import UclCmkLabelRequired from '@ucl/components/foundation-elements/CmkLabelRequired/UclCmkLabelRequired.vue'
import UclCmkSpace from '@ucl/components/foundation-elements/CmkSpace/UclCmkSpace.vue'
import UclCmkZebra from '@ucl/components/foundation-elements/CmkZebra/UclCmkZebra.vue'
import UclCmkHeading from '@ucl/components/foundation-elements/typography/UclCmkHeading.vue'
import UclCmkParagraph from '@ucl/components/foundation-elements/typography/UclCmkParagraph.vue'
import UclArrowDown from '@ucl/components/graphics/ArrowDown/UclArrowDown.vue'
import UclCmkLinkCard from '@ucl/components/navigation/CmkLinkCard/UclCmkLinkCard.vue'
import UclCmkAlertBox from '@ucl/components/system-feedback/CmkAlertBox/UclCmkAlertBox.vue'
import UclCmkCopy from '@ucl/components/system-feedback/CmkCopy/UclCmkCopy.vue'
import UclCmkCopyButton from '@ucl/components/system-feedback/CmkCopy/UclCmkCopyButton.vue'
import UclCmkDialog from '@ucl/components/system-feedback/CmkDialog/UclCmkDialog.vue'
import UclCmkErrorBoundary from '@ucl/components/system-feedback/CmkErrorBoundary/UclCmkErrorBoundary.vue'
import UclCmkHelpText from '@ucl/components/system-feedback/CmkHelpText/UclCmkHelpText.vue'
import UclCmkInlineValidation from '@ucl/components/system-feedback/CmkInlineValidation/UclCmkInlineValidation.vue'
import UclCmkLoading from '@ucl/components/system-feedback/CmkLoading/UclCmkLoading.vue'
import UclCmkPerfometer from '@ucl/components/system-feedback/CmkPerfometer/UclCmkPerfometer.vue'
import UclCmkPopup from '@ucl/components/system-feedback/CmkPopup/UclCmkPopup.vue'
import UclCmkPopupDialog from '@ucl/components/system-feedback/CmkPopupDialog/UclCmkPopupDialog.vue'
import UclCmkProgressbar from '@ucl/components/system-feedback/CmkProgressbar/UclCmkProgressbar.vue'
import UclCmkSkeleton from '@ucl/components/system-feedback/CmkSkeleton/UclCmkSkeleton.vue'
import UclCmkTooltip from '@ucl/components/system-feedback/CmkTooltip/UclCmkTooltip.vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

vi.mock('vue-router', () => ({
  useRouter: () => ({ resolve: () => ({ href: '/' }) }),
  useRoute: () => ({ query: {} })
}))

// msw/browser's setupWorker requires a real Service Worker and cannot run in jsdom.
// We replace it with a no-op so the UCL page's onBeforeMount resolves immediately.
vi.mock('msw/browser', () => ({
  setupWorker: () => ({ start: () => Promise.resolve(), stop: () => {} })
}))

// The REST API client singleton captures globalThis.fetch at import time, before any
// msw/node server patches it. Re-create it with a lazy fetch so MSW can intercept.
vi.mock('@/lib/rest-api-client/client', async (importOriginal) => {
  const mod = await importOriginal<Record<string, unknown>>()
  const createClientImpl = (await import('openapi-fetch')).default
  return {
    ...mod,
    default: createClientImpl({
      baseUrl: `${location.protocol}//${location.host}/api/internal`,
      credentials: 'include',
      headers: { Accept: 'application/json' },
      fetch: (...args: Parameters<typeof globalThis.fetch>) => globalThis.fetch(...args)
    })
  }
})

function componentPreview() {
  return screen.getByRole('region', { name: 'component preview' })
}

function expectNoRegistryError() {
  expect(screen.queryByText(/Component registry not initialized/)).toBeNull()
}

// ─── Form elements ────────────────────────────────────────────────────────────

test('CmkCheckbox page renders its component', () => {
  render(UclCmkCheckbox, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('checkbox', { name: 'Enable notifications' })
})

test('CmkConfigurationEntityDropdown page renders its component', async () => {
  const BASE = `${location.protocol}//${location.host}/api/internal`
  const server = setupServer(
    http.get(`${BASE}/domain-types/ucl_demo_entity/collections/all`, () =>
      HttpResponse.json({
        value: [
          { id: 'entity_1', title: 'First Demo Entity' },
          { id: 'entity_2', title: 'Second Demo Entity' }
        ]
      })
    )
  )
  server.listen({ onUnhandledRequest: 'bypass' })
  try {
    render(UclCmkConfigurationEntityDropdown, { props: { screenshotMode: false } })
    await within(componentPreview()).findByRole('combobox')
  } finally {
    server.close()
  }
})

test('CmkDateTimePicker page renders its component', async () => {
  render(UclCmkDateTimePicker, { props: { screenshotMode: false } })
  const preview = within(componentPreview())
  expect(await preview.findAllByRole('button')).toHaveLength(2) // calendar and time picker triggers
  expect(await preview.findAllByRole('spinbutton')).toHaveLength(3) // date input
})

test('CmkInput page renders its component', () => {
  render(UclCmkInput, { props: { screenshotMode: false } })
  const inputs = within(componentPreview()).getAllByRole<HTMLInputElement>('textbox')
  expect(inputs.some((i) => i.value === 'Checkmk Admin')).toBe(true)
})

test('CmkDropdown page renders its component', () => {
  render(UclCmkDropdown, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('combobox')
})

test('CmkDualList page renders its component', () => {
  render(UclCmkDualList, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('listbox')
})

test('CmkList page renders its component', () => {
  render(UclCmkList, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkToggleButtonGroup page renders its component', () => {
  render(UclCmkToggleButtonGroup, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkTimeSpan page renders its component', () => {
  render(UclCmkTimeSpan, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('spinbutton')
})

// ─── Basic elements ───────────────────────────────────────────────────────────

test('CmkBadge page renders its component', () => {
  render(UclCmkBadge, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('99')
})

test('CmkButton page renders its component', () => {
  render(UclCmkButton, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkButtonCancel page renders its component', () => {
  render(UclCmkButtonCancel, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkButtonSubmit page renders its component', () => {
  render(UclCmkButtonSubmit, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkChip page renders its component', () => {
  render(UclCmkChip, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkCode page renders', () => {
  const { container } = render(UclCmkCode, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkColorPicker page renders its component', () => {
  render(UclCmkColorPicker, { props: { screenshotMode: false } })
  expect(componentPreview().querySelector('input[type="color"]')).toBeTruthy()
})

test('CmkIconButton page renders its component', () => {
  render(UclCmkIconButton, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkInlineButton page renders its component', () => {
  render(UclCmkInlineButton, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkSwitch page renders its component', () => {
  render(UclCmkSwitch, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('checkbox')
})

test('CmkTag page renders its component', () => {
  render(UclCmkTag, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('Status Tag')
})

// ─── Content organization ─────────────────────────────────────────────────────

test('CmkAccordion page renders its component', () => {
  render(UclCmkAccordion, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkAccordionStepPanel page renders its component', () => {
  render(UclCmkAccordionStepPanel, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkTabs page renders its component', () => {
  render(UclCmkTabs, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('tablist')
})

test('CmkWizard page renders its component', () => {
  render(UclCmkWizard, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('heading', { name: 'Step 1: Introduction' })
})

test('CmkCatalogPanel page renders its component', () => {
  render(UclCmkCatalogPanel, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkCollapsible page renders its component', () => {
  render(UclCmkCollapsible, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkScrollContainer page renders its component', () => {
  render(UclCmkScrollContainer, { props: { screenshotMode: false } })
  within(componentPreview()).getByText(/Lorem ipsum/)
})

test('CmkSlideIn page renders its component', () => {
  render(UclCmkSlideIn, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('button', { name: 'Open Slide-In' })
})

test('CmkSlideInDialog page renders its component', () => {
  render(UclCmkSlideInDialog, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('button', { name: 'Open Dialog' })
})

// ─── Foundation elements ──────────────────────────────────────────────────────

test('CmkIcon page renders its component', () => {
  render(UclCmkIcon, { props: { screenshotMode: false } })
  within(componentPreview()).getByTitle('Help Icon')
})

test('CmkIconEmblem page renders', () => {
  const { container } = render(UclCmkIconEmblem, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkMultitoneIcon page renders', () => {
  const { container } = render(UclCmkMultitoneIcon, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkLabel page renders its component', () => {
  render(UclCmkLabel, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('Form Field')
})

test('CmkHeading page renders its component', () => {
  render(UclCmkHeading, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('heading')
})

test('CmkParagraph page renders its component', () => {
  render(UclCmkParagraph, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('The quick brown fox jumps over the lazy dog.')
})

test('CmkHtml page renders its component', () => {
  render(UclCmkHtml, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('heading', { name: 'Heading' })
})

test('CmkIndent page renders its component', () => {
  render(UclCmkIndent, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('Top Level Content')
})

test('CmkKeyboardKey page renders', () => {
  const { container } = render(UclCmkKeyboardKey, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkLabelRequired page renders its component', () => {
  render(UclCmkLabelRequired, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('Example Field Name')
})

test('CmkSpace page renders its component', () => {
  render(UclCmkSpace, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('button', { name: 'First Element' })
})

test('CmkZebra page renders its component', () => {
  render(UclCmkZebra, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByText(/Demonstration row content/)
})

// ─── Graphics ─────────────────────────────────────────────────────────────────

test('ArrowDown page renders its component', () => {
  render(UclArrowDown, { props: { screenshotMode: false } })
  expect(componentPreview().querySelector('svg')).toBeTruthy()
})

// ─── Navigation ───────────────────────────────────────────────────────────────

test('CmkLinkCard page renders its component', () => {
  render(UclCmkLinkCard, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('link')
})

// ─── System feedback ──────────────────────────────────────────────────────────

test('CmkPopup page renders its component', () => {
  render(UclCmkPopup, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('button', { name: 'Open Popup' })
})

test('CmkAlertBox page renders its component', () => {
  render(UclCmkAlertBox, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('heading', { name: 'Alert Heading' })
})

test('CmkCopyButton page renders its component', () => {
  render(UclCmkCopyButton, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkCopyIcon page renders its component', () => {
  render(UclCmkCopy, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('cmk --check myhost')
})

test('CmkDialog page renders its component', () => {
  render(UclCmkDialog, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('Dialog Title')
})

test('CmkErrorBoundary page renders its component', () => {
  render(UclCmkErrorBoundary, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('button', { name: 'Throw error' })
})

test('CmkHelpText page renders its component', () => {
  render(UclCmkHelpText, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkInlineValidation page renders its component', () => {
  render(UclCmkInlineValidation, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('This is an inline validation error message.')
})

test('CmkLoading page renders', () => {
  const { container } = render(UclCmkLoading, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkPerfometer page renders its component', () => {
  render(UclCmkPerfometer, { props: { screenshotMode: false } })
  within(componentPreview()).getByText('75 %')
})

test('CmkPopupDialog page renders', () => {
  render(UclCmkPopupDialog, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('button')
})

test('CmkProgressbar page renders its component', () => {
  render(UclCmkProgressbar, { props: { screenshotMode: false } })
  within(componentPreview()).getAllByRole('progressbar')
})

test('CmkSkeleton page renders', () => {
  const { container } = render(UclCmkSkeleton, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkTooltip page renders its component', () => {
  render(UclCmkTooltip, { props: { screenshotMode: false } })
  within(componentPreview()).getByRole('button', { name: /Interact with me/ })
})
