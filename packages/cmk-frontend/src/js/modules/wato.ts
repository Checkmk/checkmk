/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import $ from 'jquery'
import Swal, { type SweetAlertOptions } from 'sweetalert2'

import { add_class, copy_to_clipboard, has_class, remove_class } from './utils'

// ----------------------------------------------------------------------------
// General functions for WATO
// ----------------------------------------------------------------------------

interface Dialog {
  inherited_tags: Record<string, any>
  check_attributes: string[]
  aux_tags_by_tag: any
  depends_on_tags: Record<string, string[]>
  depends_on_roles: Record<string, string[]>
  volatile_topics: string[]
  user_roles: string[]
  hide_attributes: string[]
}

let dialog_properties: null | Dialog = null

export function prepare_edit_dialog(attrs: Dialog) {
  dialog_properties = attrs
}

/* Switch the visibility of all host attributes during the configuration
   of attributes of a host */
export function fix_visibility() {
  /* First collect the current selection of all host attributes.
       They are in the same table as we are */
  const current_tags = get_effective_tags()
  if (!current_tags) return
  dialog_properties = dialog_properties!
  const hide_topics = dialog_properties.volatile_topics.slice(0)
  /* Now loop over all attributes that have conditions. Those are
       stored in the global variable depends_on_tags, which is filled
       during the creation of the web page. */

  let index
  for (let i = 0; i < dialog_properties.check_attributes.length; i++) {
    const attrname: string = dialog_properties.check_attributes[i]
    /* Now comes the tricky part: decide whether that attribute should
           be visible or not: */
    let display = ''

    // Always invisible
    if (dialog_properties.hide_attributes.indexOf(attrname) > -1) {
      display = 'none'
    }

    // Visibility depends on roles
    if (display == '' && attrname in dialog_properties.depends_on_roles) {
      for (index = 0; index < dialog_properties.depends_on_roles[attrname].length; index++) {
        const role = dialog_properties.depends_on_roles[attrname][index]
        const negate = role[0] == '!'
        const rolename = negate ? role.substr(1) : role
        const have_role = dialog_properties.user_roles.indexOf(rolename) != -1
        if (have_role == negate) {
          display = 'none'
          break
        }
      }
    }

    // Visibility depends on tags
    if (display == '' && attrname in dialog_properties.depends_on_tags) {
      for (index = 0; index < dialog_properties.depends_on_tags[attrname].length; index++) {
        const tag = dialog_properties.depends_on_tags[attrname][index]
        const negate_tag = tag[0] == '!'
        const tagname = negate_tag ? tag.substr(1) : tag
        const have_tag = current_tags.indexOf(tagname) != -1
        if (have_tag == negate_tag) {
          display = 'none'
          break
        }
      }
    }

    const tableRow = document.getElementById('attr_' + attrname)
    if (tableRow instanceof HTMLTableRowElement) {
      tableRow.style.display = display

      // Prepare current visibility information which is used
      // within the attribut validation in wato
      // Hidden attributes are not validated at all
      let oAttrDisp = document.getElementById('attr_display_' + attrname) as HTMLInputElement
      if (!oAttrDisp) {
        oAttrDisp = document.createElement('input')
        oAttrDisp.name = 'attr_display_' + attrname
        oAttrDisp.id = 'attr_display_' + attrname
        oAttrDisp.type = 'hidden'
        oAttrDisp.className = 'text'
        tableRow.appendChild(oAttrDisp)
      }
      if (display == 'none') {
        // Uncheck checkboxes of hidden fields
        const input_fields = tableRow.cells[0].getElementsByTagName('input')
        const chkbox = input_fields[0]
        chkbox.checked = false
        toggle_attribute(chkbox, attrname)

        oAttrDisp.value = '0'
      } else {
        oAttrDisp.value = '1'
      }

      // There is at least one item in this topic -> show it
      const topic = tableRow.parentNode!.childNodes[0].textContent
      if (display == '') {
        index = hide_topics.indexOf(topic!)
        if (index != -1) delete hide_topics[index]
      }
    }
  }

  // FIXME: use generic identifier for each form
  const available_forms = ['form_edit_host', 'form_editfolder']
  for (let try_form = 0; try_form < available_forms.length; try_form++) {
    const my_form = document.getElementById(available_forms[try_form])
    if (my_form != null) {
      for (const child in my_form.childNodes) {
        const myFormTableRow = my_form.childNodes[child] as HTMLTableRowElement
        if (myFormTableRow.className == 'nform') {
          if (hide_topics.indexOf(myFormTableRow.childNodes[0].childNodes[0].textContent!) > -1)
            myFormTableRow.style.display = 'none'
          else myFormTableRow.style.display = ''
        }
      }
      break
    }
  }
}

/* Make attributes visible or not when clicked on a checkbox */
export function toggle_attribute(oCheckbox: HTMLInputElement, attrname: string) {
  const oEntry = document.getElementById('attr_entry_' + attrname)
  const oDefault = document.getElementById('attr_default_' + attrname)

  // Permanent invisible attributes do
  // not have attr_entry / attr_default
  if (!oEntry) {
    return
  }

  if (oCheckbox.checked) {
    oEntry.style.display = ''
    oDefault!.style.display = 'none'
  } else {
    oEntry.style.display = 'none'
    oDefault!.style.display = ''
  }
}

function get_containers() {
  return document
    .getElementById('form_edit_host')
    ?.querySelectorAll('table.nform') as NodeListOf<HTMLTableSectionElement>
}

function get_effective_tags() {
  let current_tags: string[] = []

  const containers = get_containers()!

  for (let a = 0; a < containers.length; a++) {
    const tag_container = containers[a]
    for (let i = 0; i < tag_container.rows.length; i++) {
      dialog_properties = dialog_properties!
      const row = tag_container.rows[i]
      let add_tag_id
      if (row.tagName == 'TR') {
        const legend_cell = row.cells[0]
        if (!has_class(legend_cell, 'legend')) {
          continue
        }
        const content_cell = row.cells[1]

        /*
         * If the Checkbox is unchecked try to get a value from the inherited_tags
         *
         * The checkbox may be disabled. In this case there is a hidden field with the original
         * name of the checkbox. Get that value instead of the checkbox checked state.
         */
        const input_fields = legend_cell.getElementsByTagName('input')
        if (input_fields.length == 0) continue
        const checkbox = input_fields[0]
        let attr_enabled = false
        if (checkbox.name.indexOf('ignored_') === 0) {
          const hidden_field = input_fields[input_fields.length - 1]
          attr_enabled = hidden_field.value == 'on'
        } else {
          attr_enabled = checkbox.checked
        }

        if (attr_enabled == false) {
          const attr_ident = 'attr_' + checkbox.name.replace(/.*_change_/, '')
          if (
            attr_ident in dialog_properties.inherited_tags &&
            dialog_properties.inherited_tags[attr_ident] !== null
          ) {
            add_tag_id = dialog_properties.inherited_tags[attr_ident]
          }
        } else {
          /* Find the <select>/<checkbox> object in this tr */
          let elements: HTMLCollectionOf<HTMLElement> = content_cell.getElementsByTagName('input')
          if (elements.length == 0) elements = content_cell.getElementsByTagName('select')

          if (elements.length == 0) continue

          const oElement = elements[0] as HTMLInputElement
          if (oElement.type == 'checkbox' && oElement.checked) {
            add_tag_id = oElement.name.substr(4)
          } else if (oElement.tagName == 'SELECT') {
            add_tag_id = oElement.value
          }
        }
      }

      current_tags.push(add_tag_id)
      if (dialog_properties.aux_tags_by_tag[add_tag_id]) {
        current_tags = current_tags.concat(dialog_properties.aux_tags_by_tag[add_tag_id])
      }
    }
  }
  return current_tags
}

export function randomize_secret(id: string, len: number, message: string) {
  const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()'
  const array = new Uint8Array(len)
  window.crypto.getRandomValues(array)
  let secret = ''
  for (let i = 0; i < len; i++) {
    secret += charset.charAt(array[i] % charset.length)
  }
  const oInput = document.getElementById(id) as HTMLInputElement
  oInput.value = secret

  copy_to_clipboard(secret, message)
}

export function toggle_container(id: string) {
  const obj = document.getElementById(id)
  if (has_class(obj, 'hidden')) remove_class(obj, 'hidden')
  else add_class(obj, 'hidden')
}

// ----------------------------------------------------------------------------
// Folderlist
// ----------------------------------------------------------------------------

export function open_folder(event: Event | undefined, link: string): false | void {
  const target = event!.target
  if ((target as HTMLElement).tagName != 'DIV') {
    // Skip this event on clicks on other elements than the pure div
    return false
  }

  location.href = link
}

export function toggle_folder(_event: Event | undefined, oDiv: HTMLElement, on: boolean) {
  const obj = oDiv.parentNode as HTMLElement
  const id = obj.id.substr(7)

  // If the dropdown of the current folder object is currently open, we have
  // to prevent pointer events on other folders. They would close the current
  // dropdown.
  const popup_menu = obj.querySelector('#popup_menu')
  let all_folder_divs = document.querySelectorAll("div[id^='folder_']")
  all_folder_divs.forEach((div) => {
    if (div.id.endsWith(id)) return

    if (popup_menu) {
      ;(div as HTMLElement).style.pointerEvents = 'none'
    } else {
      ;(div as HTMLElement).style.pointerEvents = 'auto'
    }
  })

  const elements = ['edit', 'popup_trigger_move', 'delete']
  for (const num in elements) {
    const elem = document.getElementById(elements[num] + '_' + id)
    if (elem) {
      if (on) {
        elem.style.display = 'inline'
      } else {
        elem.style.display = 'none'
      }
    }
  }

  if (on) {
    add_class(obj, 'open')
  } else {
    remove_class(obj, 'open')

    // Hide the eventual open move dialog
    const move_dialog = document.getElementById('move_dialog_' + id)
    if (move_dialog) {
      move_dialog.style.display = 'none'
    }
  }
}

export function toggle_rule_condition_type(select_id: string) {
  const value = (document.getElementById(select_id) as HTMLInputElement).value
  $('.condition').hide()
  $('.condition.' + value).show()
}

export function toggle_test_notification_visibility(
  source: string,
  target: string,
  hide_options: boolean
) {
  const source_element = document.getElementsByClassName(source)[0] as HTMLInputElement
  const target_element = document.getElementsByClassName(target)[0] as HTMLInputElement
  if (source_element && target_element) {
    if (has_class(target_element, 'active')) {
      remove_class(target_element, 'active')
    }
    add_class(source_element, 'active')
  }
  toggle_test_notification_options(hide_options)
  toggle_test_notification_submit(hide_options)
}

function toggle_test_notification_options(hide_options: boolean) {
  const service_choice = document.getElementById('general_opts_d_on_service_hint') as HTMLDivElement
  const service_states = document.getElementById(
    'general_opts_p_simulation_mode_1_d_svc_states'
  ) as HTMLDivElement
  const host_states = document.getElementById(
    'general_opts_p_simulation_mode_1_d_host_states'
  ) as HTMLDivElement
  if (service_choice && service_states && host_states) {
    const service_choice_tr = service_choice.parentNode!.parentNode as HTMLElement
    const service_states_tr = service_states.parentNode!.parentNode as HTMLElement
    const host_states_tr = host_states.parentNode!.parentNode as HTMLElement
    if (!service_choice_tr || !service_states_tr || !host_states_tr) {
      return
    }

    const service_choice_selection = document.getElementById(
      'general_opts_p_on_service_hint'
    ) as HTMLSelectElement
    if (hide_options) {
      add_class(service_choice_tr, 'hidden')
      add_class(service_states_tr, 'hidden')

      if (service_choice_selection) {
        service_choice_selection.disabled = true
      }
      remove_class(host_states_tr, 'hidden')
    } else {
      remove_class(service_choice_tr, 'hidden')
      remove_class(service_states_tr, 'hidden')

      if (service_choice_selection) {
        service_choice_selection.disabled = false
      }

      add_class(host_states_tr, 'hidden')
    }
  }
}

function toggle_test_notification_submit(hide_options: boolean) {
  const submit_button = document.getElementById('_test_host_notifications') as HTMLDivElement
  if (submit_button) {
    if (hide_options) {
      submit_button.setAttribute('name', '_test_host_notifications')
    } else {
      submit_button.setAttribute('name', '_test_service_notifications')
    }
  }
}

type MessageType = 'crit' | 'warn' | 'info' | 'success'

export function message(message_text: string, message_type: MessageType, del_var: string) {
  const iconFilenames = {
    crit: 'icon_alert.crit.svg',
    warn: 'icon_problem.svg',
    info: 'icon_message.svg',
    success: 'icon_checkmark.svg'
  }

  const filename = iconFilenames[message_type] ?? iconFilenames['info']

  const args: SweetAlertOptions = {
    // https://sweetalert2.github.io/#configuration
    target: '#page_menu_popups',
    text: message_text,
    animation: false,
    position: 'top-start',
    grow: 'row',
    allowOutsideClick: false,
    backdrop: false,
    buttonsStyling: false,
    showConfirmButton: false,
    showCloseButton: true,
    iconHtml: `<img src="themes/facelift/images/${filename}">`,
    didOpen: () => {
      // Remove focus on CloseButton
      const closeButton = document.querySelector('.swal2-close') as HTMLButtonElement
      if (closeButton) {
        closeButton.blur()
      }
    },
    customClass: {
      container: 'message_container',
      popup: 'message_popup',
      htmlContainer: 'message_content',
      icon: `confirm_icon message_${message_type}`,
      closeButton: 'message_close'
    }
  }

  Swal.fire(args)

  // Remove the var to not get the message twice on reload
  const params = new URLSearchParams(window.location.search)
  params.delete(del_var)
  // And update the URL without reloading the page
  window.history.replaceState(null, '', window.location.pathname + '?' + params.toString())
}
