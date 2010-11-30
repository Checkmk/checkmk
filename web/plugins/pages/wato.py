import wato
import sidebar

pagehandlers.update({
    "wato"            : wato.page_index,
    "ajax_wato_files" : sidebar.ajax_wato_files,
})
