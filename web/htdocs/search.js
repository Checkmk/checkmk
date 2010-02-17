var aSearchResults = [];
var iCurrent = null;
var mkSearchTargetFrame = 'main';
var mkSearchCheckMkUrl = '/check_mk';

// Register an input field to be a search field and add eventhandlers
function mkSearchAddField(field, targetFrame, checkMkUrl) {
    var oField = document.getElementById(field);

    if(oField) {
				if(typeof targetFrame != 'undefined') {
					mkSearchTargetFrame = targetFrame;
				}
		
				if(typeof checkMkUrl != 'undefined') {
					mkSearchcheckMkUrl = checkMkUrl;
				}
		
        oField.onkeydown   = function(e) { if (!e) e = window.event; return mkSearchKeyDown(e, oField); }
        oField.onkeyup     = function(e) { if (!e) e = window.event; return mkSearchKeyUp(e, oField);}
        oField.onclick     = function(e) { if (!e) e = window.event; e.cancelBubble = true; e.returnValue = false; }
				// The keypress event is being ignored. Key presses are handled by onkeydown and onkeyup events
        oField.onkeypress  = function(e) { if (!e) e = window.event; if (e.keyCode == 13) return false; }

        // On doubleclick toggle the list
        oField.ondblclick  = function(e) { if (!e) e = window.event; mkSearchToggle(e, oField); }
    }
}

// On key release event handler
function mkSearchKeyUp(e, oField) {
	var keyCode = e.which || e.keyCode;

	switch (keyCode) {
		// Return/Enter
		case 13:
			e.returnValue = false;
			e.cancelBubble = true;
		break;

		// Escape
		case 27:
			mkSearchClose();
			e.returnValue = false;
			e.cancelBubble = true;
		break;
		
		// Up/Down
		case 38:
		case 40:
			return false;
		break;

		// Other keys
		default:
			mkSearch(e, oField);
		break;
	}
}

// On key press down event handler
function mkSearchKeyDown(e, oField) {
    var keyCode = e.which || e.keyCode;

    switch (keyCode) {
			// Return/Enter
			case 13:
				if (iCurrent != null) {
					mkSearchNavigate();
					mkSearchClose();
				} else {
					// When nothing selected, navigate with the current contents of the field
					top.frames[mkSearchTargetFrame].location.href = mkSearchCheckMkUrl+'/view.py?view_name=host&host='+oField.value;
					mkSearchClose();
				}
				
				e.returnValue = false;
				e.cancelBubble = true;
			break;
			
			// Escape
			case 27:
				mkSearchClose();
				e.returnValue = false;
				e.cancelBubble = true;
			break;
			
			// Up arrow
			case 38:
				if(!mkSearchResultShown()) {
					mkSearch(e, oField);
				}
				
				mkSearchMoveElement(-1);
				return false;
			break;
			
			// Tab
			case 9:
				if(mkSearchResultShown()) {
					mkSearchClose();
				}
				return;
			break;
			
			// Down arrow
			case 40:
				if(!mkSearchResultShown()) {
					mkSearch(e, oField);
				}
				
				mkSearchMoveElement(1);
				return false;
			break;
		}
}

// Navigate to the target of the selected event
function mkSearchNavigate() {
	top.frames[mkSearchTargetFrame].location.href = aSearchResults[iCurrent].url;
}

// Move one step of given size in the result list
function mkSearchMoveElement(step) {
	if(iCurrent == null) {
		iCurrent = -1;
	}

	iCurrent += step;

	if(iCurrent < 0)
		iCurrent = aSearchResults.length-1;
	
	if(iCurrent > aSearchResults.length-1)
		iCurrent = 0;

	var oResults = document.getElementById('mk_search_results').childNodes;
	var a = 0;
	for(var i in oResults) {
		if(oResults[i].nodeName == 'A') {
			if(a == iCurrent) {
				oResults[i].setAttribute('class', 'active');
				oResults[i].setAttribute('className', 'active');
			} else {
				oResults[i].setAttribute('class', 'inactive');
				oResults[i].setAttribute('className', 'inactive');
			}
			a++;
		}
	}
}

// Is the result list shown at the moment?
function mkSearchResultShown() {
	var oContainer = document.getElementById('mk_search_results');
	if(oContainer) {
		oContainer = null;
		return true;
	} else
		return false;
}

// Toggle the result list
function mkSearchToggle(e, oField) {
	if(mkSearchResultShown()) {
		mkSearchClose();
	} else {
		mkSearch(e, oField);
	}
}

// Close the result list
function mkSearchClose() {
  var oContainer = document.getElementById('mk_search_results');
  if(oContainer) {
    oContainer.parentNode.removeChild(oContainer);
    oContainer = null;
  }
	
	aSearchResults = [];
	iCurrent = null;
}

// Build a new result list and show it up
function mkSearch(e, oField) {
    var val = oField.value;

    if(!aSearchHosts) {
        alert("No hosts to search for");
				return;
		}

		aSearchResults = [];

    // Build matching regex
    var oMatch = new RegExp('^'+val, 'gi');

    var content = '';
    var hostName, hostAlias;
    for(var i in aSearchHosts){
        hostName = aSearchHosts[i][0];
        hostAlias = aSearchHosts[i][1];

        if(hostName.match(oMatch) || hostAlias.match(oMatch)) {
						var oResult = {
							'id': 'result_'+hostName,
							'name': hostName,
							'url': mkSearchCheckMkUrl+'/view.py?view_name=/host&host='+hostName,
						};
						
						// Add id to search result array
						aSearchResults.push(oResult);
						
            content += '<a id="'+oResult.id+'" href="'+oResult.url+'" onclick="mkSearchClose()" target="'+mkSearchTargetFrame+'">'+hostAlias+" ("+hostName+")</a>\n";
        }
    }
		
    if(content != '') {
        var oContainer = document.getElementById('mk_search_results');
        if(!oContainer) {
            var oContainer = document.createElement('div');
            oContainer.setAttribute('id', 'mk_search_results');
        }

        oContainer.innerHTML = content;

        oField.parentNode.appendChild(oContainer);

        oContainer = null;
    } else {
			mkSearchClose();
		}
    
    oField = null;
}
