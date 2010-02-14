function addField(field) {
    var oField = document.getElementById(field);

    if(oField) {
        //field.onkeydown  = function(e) {return AutoComplete_KeyDown(this.getAttribute('id'), e);}
        //field.onkeyup    = function(e) {return AutoComplete_KeyUp(this.getAttribute('id'), e);}
        //field.ondblclick = function() {AutoComplete_ShowDropdown(this.getAttribute('id'));}
        //field.onclick    = function(e) {if (!e) e = window.event; e.cancelBubble = true; e.returnValue = false;}

				// On doubleclick toggle the list
				oField.ondblclick = function() {
            mkSideSearchToggle(oField);
				}

        oField.onkeypress = function(e) { 
            if (!e) e = window.event;
            mkSideSearch(oField);
						
						// On "enter" key open the current host instant
            if (e.keyCode == 13) {
							top.frames['main'].location.href = '/nagios/cgi-bin/status.cgi?host='+oField.value;
						}
        }
    }
}

function mkSideSearchToggle(oField) {
	var oContainer = document.getElementById('mk_search_results');
	if(oContainer) {
		mkSideSearchClose();
	} else {
		mkSideSearch(oField);
	}
}

function mkSideSearchClose() {
  var oContainer = document.getElementById('mk_search_results');
  if(oContainer) {
    oContainer.parentNode.removeChild(oContainer);
    oContainer = null;
  }
}

function mkSideSearch(oField) {
    var val = oField.value;

    if(!aSearchHosts)
        alert("No hosts to search for");

    // Build matching regex
    var oMatch = new RegExp('^'+val, 'gi');

    var oContainer = document.getElementById('mk_search_results');
    if(!oContainer) {
      var oContainer = document.createElement('div');
      oContainer.setAttribute('id', 'mk_search_results');
    }

    var content = '';
    var hostName, hostAlias;
    for(var i in aSearchHosts){
        hostName = aSearchHosts[i][0];
        hostAlias = aSearchHosts[i][1];

        if(hostName.match(oMatch) || hostAlias.match(oMatch)) {
            // FIXME: Hardcoded path, frame
            content += '<a href="/nagios/cgi-bin/status.cgi?host='+hostName+'" onclick="mkSideSearchClose()" target="main">'+hostAlias+" ("+hostName+")</a>\n";
        }
    }

    oContainer.innerHTML = content;

    oField.parentNode.appendChild(oContainer);

    oContainer = null;
    oField = null;
}
