/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import UclCmkBadge from '@ucl/components/basic-elements/CmkBadge/UclCmkBadge.vue'
import UclCmkButton from '@ucl/components/basic-elements/CmkButton/UclCmkButton.vue'
import UclCmkChip from '@ucl/components/basic-elements/CmkChip/UclCmkChip.vue'
import UclCmkCode from '@ucl/components/basic-elements/CmkCode/UclCmkCode.vue'
import UclCmkColorPicker from '@ucl/components/basic-elements/CmkColorPicker/UclCmkColorPicker.vue'
import UclCmkSwitch from '@ucl/components/basic-elements/CmkSwitch/UclCmkSwitch.vue'
import UclCmkTag from '@ucl/components/basic-elements/CmkTag/UclCmkTag.vue'
import UclCmkAccordion from '@ucl/components/content-organization/CmkAccordion/UclCmkAccordion.vue'
import UclAccordionCmkStepPanel from '@ucl/components/content-organization/CmkAccordionStepPanel/UclAccordionCmkStepPanel.vue'
import UclCmkCatalogPanel from '@ucl/components/content-organization/CmkCatalogPanel/UclCmkCatalogPanel.vue'
import UclCmkCollapsible from '@ucl/components/content-organization/CmkCollapsible/UclCmkCollapsible.vue'
import UclCmkScrollContainer from '@ucl/components/content-organization/CmkScrollContainer/UclCmkScrollContainer.vue'
import UclCmkSlideIn from '@ucl/components/content-organization/CmkSlideIn/UclCmkSlideIn.vue'
import UclCmkSlideInDialog from '@ucl/components/content-organization/CmkSlideInDialog/UclCmkSlideInDialog.vue'
import UclCmkTabs from '@ucl/components/content-organization/CmkTabs/UclCmkTabs.vue'
import UclCmkWizard from '@ucl/components/content-organization/CmkWizard/UclCmkWizard.vue'
import UclTwoFactorAuthentication from '@ucl/components/content-organization/TwoFactorAuthentication/UclTwoFactorAuthentication.vue'
import UclCmkCheckbox from '@ucl/components/form-elements/CmkCheckbox/UclCmkCheckbox.vue'
import UclCmkDropdown from '@ucl/components/form-elements/CmkDropdown/UclCmkDropdown.vue'
import UclCmkDualList from '@ucl/components/form-elements/CmkDualList/UclCmkDualList.vue'
import UclCmkInput from '@ucl/components/form-elements/CmkInput/UclCmkInput.vue'
import UclCmkList from '@ucl/components/form-elements/CmkList/UclCmkList.vue'
import UclCmkToggleButtonGroup from '@ucl/components/form-elements/CmkToggleButtonGroup/UclCmkToggleButtonGroup.vue'
import UclCmkHtml from '@ucl/components/foundation-elements/CmkHtml/UclCmkHtml.vue'
import UclCmkIcon from '@ucl/components/foundation-elements/CmkIcon/UclCmkIcon.vue'
import UclCmkIconEmblem from '@ucl/components/foundation-elements/CmkIcon/UclCmkIconEmblem.vue'
import UclCmkMultitoneIcon from '@ucl/components/foundation-elements/CmkIcon/UclCmkMultitoneIcon.vue'
import UclCmkIndent from '@ucl/components/foundation-elements/CmkIndent/UclCmkIndent.vue'
import UclCmkKeyboardKey from '@ucl/components/foundation-elements/CmkKeyboardKey/UclCmkKeyboardKey.vue'
import UclCmkLabelRequired from '@ucl/components/foundation-elements/CmkLabelRequired/UclCmkLabelRequired.vue'
import UclCmkSpace from '@ucl/components/foundation-elements/CmkSpace/UclCmkSpace.vue'
import UclCmkZebra from '@ucl/components/foundation-elements/CmkZebra/UclCmkZebra.vue'
import UclCmkHeading from '@ucl/components/foundation-elements/typography/UclCmkHeading.vue'
import UclCmkParagraph from '@ucl/components/foundation-elements/typography/UclCmkParagraph.vue'
import UclCmkLinkCard from '@ucl/components/navigation/CmkLinkCard/UclCmkLinkCard.vue'
import UclCmkAlertBox from '@ucl/components/system-feedback/CmkAlertBox/UclCmkAlertBox.vue'
import UclCmkCopyButton from '@ucl/components/system-feedback/CmkCopy/UclCmkCopyButton.vue'
import UclCmkCopyIcon from '@ucl/components/system-feedback/CmkCopy/UclCmkCopyIcon.vue'
import UclCmkDialog from '@ucl/components/system-feedback/CmkDialog/UclCmkDialog.vue'
import UclCmkErrorBoundary from '@ucl/components/system-feedback/CmkErrorBoundary/UclCmkErrorBoundary.vue'
import UclCmkHelp from '@ucl/components/system-feedback/CmkHelp/UclCmkHelp.vue'
import UclCmkInlineValidation from '@ucl/components/system-feedback/CmkInlineValidation/UclCmkInlineValidation.vue'
import UclCmkLoading from '@ucl/components/system-feedback/CmkLoading/UclCmkLoading.vue'
import UclCmkPerfometer from '@ucl/components/system-feedback/CmkPerfometer/UclCmkPerfometer.vue'
import UclCmkPopupDialog from '@ucl/components/system-feedback/CmkPopupDialog/UclCmkPopupDialog.vue'
import UclCmkProgressbar from '@ucl/components/system-feedback/CmkProgressbar/UclCmkProgressbar.vue'
import UclCmkSkeleton from '@ucl/components/system-feedback/CmkSkeleton/UclCmkSkeleton.vue'
import UclCmkTooltip from '@ucl/components/system-feedback/CmkTooltip/UclCmkTooltip.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ resolve: () => ({ href: '/' }) }),
  useRoute: () => ({ query: {} })
}))

function expectNoRegistryError() {
  expect(screen.queryByText(/Component registry not initialized/)).toBeNull()
}

// ─── Form elements ────────────────────────────────────────────────────────────

test('CmkCheckbox demo page renders its component', () => {
  render(UclCmkCheckbox, { props: { screenshotMode: false } })
  screen.getByRole('checkbox', { name: 'Enable notifications' })
})

test('CmkInput demo page renders its component', () => {
  render(UclCmkInput, { props: { screenshotMode: false } })
  const inputs = screen.getAllByRole<HTMLInputElement>('textbox')
  expect(inputs.some((i) => i.value === 'Checkmk Admin')).toBe(true)
})

test('CmkDropdown demo page renders its component', () => {
  render(UclCmkDropdown, { props: { screenshotMode: false } })
  screen.getAllByRole('combobox')
})

test('CmkDualList demo page renders its component', () => {
  render(UclCmkDualList, { props: { screenshotMode: false } })
  screen.getAllByRole('listbox')
})

test('CmkList demo page renders its component', () => {
  render(UclCmkList, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkToggleButtonGroup demo page renders its component', () => {
  render(UclCmkToggleButtonGroup, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

// ─── Basic elements ───────────────────────────────────────────────────────────

test('CmkBadge demo page renders its component', () => {
  render(UclCmkBadge, { props: { screenshotMode: false } })
  screen.getByText('99')
})

test('CmkButton demo page renders its component', () => {
  render(UclCmkButton, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkChip demo page renders its component', () => {
  render(UclCmkChip, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkCode demo page renders', () => {
  const { container } = render(UclCmkCode, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkColorPicker demo page renders its component', () => {
  render(UclCmkColorPicker, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkSwitch demo page renders its component', () => {
  render(UclCmkSwitch, { props: { screenshotMode: false } })
  screen.getAllByRole('checkbox')
})

test('CmkTag demo page renders its component', () => {
  render(UclCmkTag, { props: { screenshotMode: false } })
  screen.getByText('Status Tag')
})

// ─── Content organization ─────────────────────────────────────────────────────

test('CmkAccordion demo page renders its component', () => {
  render(UclCmkAccordion, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkAccordionStepPanel demo page renders its component', () => {
  render(UclAccordionCmkStepPanel, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkTabs demo page renders its component', () => {
  render(UclCmkTabs, { props: { screenshotMode: false } })
  screen.getByRole('tablist')
})

test('CmkWizard demo page renders its component', () => {
  render(UclCmkWizard, { props: { screenshotMode: false } })
  screen.getByRole('heading', { name: 'Step 1: Introduction' })
})

test('CmkCatalogPanel demo page renders its component', () => {
  render(UclCmkCatalogPanel, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkCollapsible demo page renders its component', () => {
  render(UclCmkCollapsible, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkScrollContainer demo page renders its component', () => {
  render(UclCmkScrollContainer, { props: { screenshotMode: false } })
  screen.getByText(/Lorem ipsum/)
})

test('CmkSlideIn demo page renders its component', () => {
  render(UclCmkSlideIn, { props: { screenshotMode: false } })
  screen.getByRole('heading', { name: 'CmkSlideIn' })
})

test('CmkSlideInDialog demo page renders its component', () => {
  render(UclCmkSlideInDialog, { props: { screenshotMode: false } })
  screen.getByRole('heading', { name: 'CmkSlideInDialog' })
})

test('TwoFactorAuthentication demo page renders', () => {
  const { container } = render(UclTwoFactorAuthentication, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

// ─── Foundation elements ──────────────────────────────────────────────────────

test('CmkIcon demo page renders its component', () => {
  render(UclCmkIcon, { props: { screenshotMode: false } })
  screen.getByTitle('Help Icon')
})

test('CmkIconEmblem demo page renders', () => {
  const { container } = render(UclCmkIconEmblem, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkMultitoneIcon demo page renders', () => {
  const { container } = render(UclCmkMultitoneIcon, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkHeading demo page renders its component', () => {
  render(UclCmkHeading, { props: { screenshotMode: false } })
  screen.getAllByRole('heading')
})

test('CmkParagraph demo page renders its component', () => {
  render(UclCmkParagraph, { props: { screenshotMode: false } })
  screen.getByText('The quick brown fox jumps over the lazy dog.')
})

test('CmkHtml demo page renders its component', () => {
  render(UclCmkHtml, { props: { screenshotMode: false } })
  screen.getByRole('heading', { name: 'Heading' })
})

test('CmkIndent demo page renders its component', () => {
  render(UclCmkIndent, { props: { screenshotMode: false } })
  screen.getByText('Top Level Content')
})

test('CmkKeyboardKey demo page renders', () => {
  const { container } = render(UclCmkKeyboardKey, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkLabelRequired demo page renders its component', () => {
  render(UclCmkLabelRequired, { props: { screenshotMode: false } })
  screen.getByText('Example Field Name')
})

test('CmkSpace demo page renders its component', () => {
  render(UclCmkSpace, { props: { screenshotMode: false } })
  screen.getByRole('button', { name: 'First Element' })
})

test('CmkZebra demo page renders its component', () => {
  render(UclCmkZebra, { props: { screenshotMode: false } })
  screen.getAllByText(/Demonstration row content/)
})

// ─── Navigation ───────────────────────────────────────────────────────────────

test('CmkLinkCard demo page renders its component', () => {
  render(UclCmkLinkCard, { props: { screenshotMode: false } })
  screen.getAllByRole('link')
})

// ─── System feedback ──────────────────────────────────────────────────────────

test('CmkAlertBox demo page renders its component', () => {
  render(UclCmkAlertBox, { props: { screenshotMode: false } })
  screen.getByRole('heading', { name: 'Alert Heading' })
})

test('CmkCopyButton demo page renders its component', () => {
  render(UclCmkCopyButton, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkCopyIcon demo page renders its component', () => {
  render(UclCmkCopyIcon, { props: { screenshotMode: false } })
  screen.getByText('cmk --check myhost')
})

test('CmkDialog demo page renders its component', () => {
  render(UclCmkDialog, { props: { screenshotMode: false } })
  screen.getByText('Dialog Title')
})

test('CmkErrorBoundary demo page renders its component', () => {
  render(UclCmkErrorBoundary, { props: { screenshotMode: false } })
  screen.getByRole('button', { name: 'Throw error' })
})

test('CmkHelpText demo page renders its component', () => {
  render(UclCmkHelp, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkInlineValidation demo page renders its component', () => {
  render(UclCmkInlineValidation, { props: { screenshotMode: false } })
  screen.getByText('This is an inline validation error message.')
})

test('CmkLoading demo page renders', () => {
  const { container } = render(UclCmkLoading, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkPerfometer demo page renders its component', () => {
  render(UclCmkPerfometer, { props: { screenshotMode: false } })
  screen.getByText('75 %')
})

test('CmkPopupDialog demo page renders', () => {
  render(UclCmkPopupDialog, { props: { screenshotMode: false } })
  screen.getAllByRole('button')
})

test('CmkProgressbar demo page renders its component', () => {
  render(UclCmkProgressbar, { props: { screenshotMode: false } })
  screen.getAllByRole('progressbar')
})

test('CmkSkeleton demo page renders', () => {
  const { container } = render(UclCmkSkeleton, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
  expectNoRegistryError()
})

test('CmkTooltip demo page renders its component', () => {
  render(UclCmkTooltip, { props: { screenshotMode: false } })
  screen.getByRole('button', { name: /Interact with me/ })
})
