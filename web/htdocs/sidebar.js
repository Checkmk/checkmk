// Load stylesheet for sidebar

// Get object of script (myself)
var oSidebar = document.getElementById("check_mk_sidebar");

var url = '';
for(var i in oSidebar.childNodes)
	if(oSidebar.childNodes[i].nodeName == 'SCRIPT') {
		url = oSidebar.childNodes[i].src.replace("sidebar.js", "");
		break;
	}

if(url == '')
	alert('ERROR: Unable to determine the script location. Problem finding sidebar.js inside the check_mk_sidebar container.');


var oLink = document.createElement('link')
oLink.href = url + "check_mk.css";
oLink.rel = 'stylesheet';
oLink.type = 'text/css';
document.body.appendChild(oLink);

document.write(get_url(url + 'sidebar.py'));

// Cleaning up DOM links
oLink = null;
oSidebar = null;

function get_url(url) {
      if (window.XMLHttpRequest) {              
          AJAX=new XMLHttpRequest();              
      } else {                                  
          AJAX=new ActiveXObject("Microsoft.XMLHTTP");
      }
      if (AJAX) {
         AJAX.open("GET", url, false);                             
         AJAX.send(null);
         return AJAX.responseText;                                         
      } else {
         return false;
      }                                             
}

function toggle_sidebar_snapin(oH2, url) {
    var oContent = oH2.parentNode.childNodes[3];
    var closed = oContent.style.display == "none";
    if (closed)
	oContent.style.display = "";
    else
	oContent.style.display = "none";
    /* make this persistent -> save */
    get_url(url + (closed ? "open" : "closed")); 
    oContent = null;
}

function switch_site(baseuri, switchvar) {
    get_url(baseuri + "/switch_site.py?" + switchvar);
    parent.frames[1].location.reload(); /* reload main frame */
}


function sidebar_scheduler() {
    var timestamp = Date.parse(new Date()) / 1000;
    var newcontent = "";
    for (var i in refresh_snapins) { 
	name    = refresh_snapins[i][0];
	refresh = refresh_snapins[i][1];
	if (timestamp % refresh == 0) {
	    newcontent = get_url(url + "/sidebar_snapin.py?name=" + name);
	    var oSnapin = document.getElementById("snapin_" + name);
	    oSnapin.innerHTML = newcontent;
	    oSnapin = null;
	}
    }
    setTimeout(function(){sidebar_scheduler();}, 1000);
}
