// Load stylesheet for sidebar

// Get object of script (myself)
var oScript = document.getElementById("check_mk_sidebar").childNodes[0];
var url = oScript.src.replace("sidebar.js", "");

var oLink = document.createElement('link')
oLink.href = url + "check_mk.css";
oLink.rel = 'stylesheet';
oLink.type = 'text/css';
document.body.appendChild(oLink);
oLink = null;

function getFile(url) {
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

document.write(getFile(url + 'sidebar.py'));
