// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
// 
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
// 
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

//
// Sidebar styling and scrolling stuff
//

/************************************************
 * snapin drag/drop code
 *************************************************/

var snapinDragging = false;
var snapinOffset   = [ 0, 0 ];
var snapinStartPos = [ 0, 0 ];

if(window.addEventListener) {
  window.addEventListener("mousemove", snapinDrag,      false);
} else {
  document.documentElement.onmousemove = snapinDrag;
}

function snapinStartDrag(event) {
  // IE fix
  if (!event)
    event = window.event;
  
  // Skip calls when already dragging or other button than left mouse
  if(snapinDragging !== false || event.button != 0 || event.target.tagName != 'DIV')
    return true;

  var container = event.target.parentNode;
  
  if(event.preventDefault)
    event.preventDefault();
  event.returnValue = false;
  
  if(event.stopPropagation)
    event.stopPropagation();
  event.cancelBubble = true;
  
  snapinDragging = container;

  // Save relative offset of the mouse to the snapin title to prevent flipping on drag start
  snapinOffset   = [ event.clientY - container.offsetTop, event.clientX - container.offsetLeft ];
  snapinStartPos = [ event.clientY, event.clientX ];
}

function snapinDrag(event) {
  // IE fix
  if (!event)
    event = window.event;
  
  if(snapinDragging === false)
    return true;

  // Drag the snapin
  snapinDragging.style.position = 'absolute';
  snapinDragging.style.top      = event.clientY - snapinOffset[0];
  snapinDragging.style.left     = event.clientX - snapinOffset[1];
  snapinDragging.style.width    = '175px';
  snapinDragging.style.zIndex   = 200;

  // Refresh the drop marker
  removeSnapinDragIndicator();
  
  var line = document.createElement('div');
  line.setAttribute('id', 'snapinDragIndicator');
  line.style.height          = '4px';
  line.style.backgroundColor = '#ff0000';
  var o = getSnapinTargetPos();
  if(o != null) {
    snapinAddBefore(o.parentNode, o, line);
    o = null;
  } else {
    snapinAddBefore(snapinDragging.parentNode, null, line);
  }
  line = null;
}

function snapinAddBefore(par, o, add) {
  if(o != null) {
    par.insertBefore(add, o);
    o = null;
  } else {
    par.appendChild(add);
  }
  add = null;
}

function removeSnapinDragIndicator() {
  var o = document.getElementById('snapinDragIndicator');
  if(o) {
    o.parentNode.removeChild(o);
    o = null;
  }
}

function snapinDrop(event, o) {
  if(snapinDragging == false)
    return true;

  // Reset properties
  snapinDragging.style.top      = '';
  snapinDragging.style.left     = '';
  snapinDragging.style.position = '';

  // Catch quick clicks without movement on the title bar
  // Don't reposition the object in this case.
  if(snapinStartPos[0] == event.clientY && snapinStartPos[1] == event.clientX) {
    if(event.preventDefault)
      event.preventDefault();
    if(event.stopPropagation)
      event.stopPropagation();
    event.returnValue = false;
    return false;
  }
  
  var par = snapinDragging.parentNode;
  par.removeChild(snapinDragging);
  snapinAddBefore(par, o, snapinDragging);

  // Now send the new information to the backend
  var thisId = snapinDragging.id.replace('snapin_container_', '');

  var after = '';
  if(o != null)
    after = '&after='+o.id.replace('snapin_container_', '');
  get_url('reposition_snapin.py?name='+thisId+after);
  thisId = null;
  o = null;
}

function snapinStopDrag(event) {
  // IE fix
  if (!event)
    event = window.event;
  
  removeSnapinDragIndicator();
  snapinDrop(event, getSnapinTargetPos());
  snapinDragging = false;
}

function getSnapinTargetPos() {
  var snapinTop = snapinDragging.offsetTop;
  var childs = snapinDragging.parentNode.children;
  var obj = false;
  
  // Find the nearest snapin to current left/top corner of
  // the currently dragged snapin
  for(var i in childs) {
    child = childs[i];

    // Skip currently dragged object
    if(child == snapinDragging)
      continue;
    
    // Initialize with the first snapin in the list
    if(obj === false) {
      obj = child;
      continue;
    }

    // First check which corner is closer. Upper left or
    // the bottom left.
    var curBottomOffset = obj.offsetTop + obj.clientHeight - snapinTop;
    if(curBottomOffset < 0)
      curBottomOffset *= -1;

    var curTopOffset = obj.offsetTop - snapinTop;
    if(curTopOffset < 0)
      curTopOffset *= -1;

    var curOffset = curTopOffset;
    if(curBottomOffset < curTopOffset)
      curOffset = curBottomOffset;
    
    var newBottomOffset = child.offsetTop + obj.clientHeight - snapinTop
    if(newBottomOffset < 0)
      newBottomOffset *= -1;
    
    var newTopOffset = child.offsetTop - snapinTop
    if(newTopOffset < 0)
      newTopOffset *= -1;

    var newOffset = newTopOffset;
    if(newBottomOffset < newTopOffset)
      newOffset = newBottomOffset;

    // Is the upper left corner closer?
    if(curOffset > newOffset) {
      obj = child;
      continue;
    }
  }

  // Is the dragged snapin dragged below the last one?
  if((obj.id == childs[childs.length-1].id && snapinTop > obj.offsetTop + obj.clientHeight)
     || (snapinDragging == childs[childs.length-1] && snapinTop > childs[childs.length-2].offsetTop + childs[childs.length-2].clientHeight)) {
    return null;
  }

  return obj;
}

/************************************************
 * misc sidebar styling
 *************************************************/

function pageHeight() {
  var h;

  if(window.innerHeight !== null && typeof window.innerHeight !== 'undefined')
    h = window.innerHeight;
  else if(document.documentElement && document.documentElement.clientHeight)
    h = document.documentElement.clientHeight;
  else if(document.body !== null)
    h = document.body.clientHeight;
  else
    h = null;

  return h;
}

// Set the size of the sidebar_content div to fit the whole screen
// but without scrolling. The height of the header and footer divs need
// to be treated here.
function setSidebarHeight() {
  var oHeader  = document.getElementById('side_header');
  var oContent = document.getElementById('side_content');
  var oFooter  = document.getElementById('side_footer');
  var height   = pageHeight();

  oContent.style.height = height - oHeader.clientHeight - oFooter.clientHeight;
}

var scrolling = true;

function scrollwindow(speed){
  var c = document.getElementById('side_content');

  if(scrolling) {
    c.scrollTop += speed;
    setTimeout("scrollwindow("+speed+")", 10);
  }

  c = null;
}

/************************************************
 * drag/drop scrollen
 *************************************************/
 
var dragging = false;
var startY = 0;
var startScroll = 0;

if(window.addEventListener) {
  window.addEventListener("mousedown", startDragScroll, false);
  window.addEventListener("mouseup",   stopDragScroll,  false);
  window.addEventListener("mousemove", dragScroll,      false);
} else {
  document.documentElement.onmousedown = startDragScroll;
  document.documentElement.onmouseup   = stopDragScroll;
  document.documentElement.onmousemove = dragScroll;
}

function startDragScroll(event) {
  // IE fix
  if (!event)
    event = window.event;
  
  // Evtl. auch nur mit Shift Taste: (e.button == 0 && (e["shiftKey"])
  if(dragging === false && event.button == 0
     && event.target.tagName != 'A'
     && event.target.tagName != 'INPUT'
     && !(event.target.tagName == 'DIV' && event.target.className == 'heading')) {
    event.preventDefault();
    event.stopPropagation();
    event.returnValue = false;
    
    dragging = event;
    startY = event.clientY;
    startScroll = document.getElementById('side_content').scrollTop;
  }
}

function stopDragScroll(event){ 
  dragging = false;
}

function dragScroll(event) {
  // IE fix
  if (!event)
    event = window.event;
  
  if(dragging === false)
    return true;
  
  if(event.preventDefault)
    event.preventDefault();
  event.returnValue = false;
  
  if(event.stopPropagation)
    event.stopPropagation();
  event.cancelBubble = true;
  
  var inhalt = document.getElementById('side_content');
  var diff = startY - event.clientY;
  
  //parent.main.document.close(); 
  //parent.main.document.open(); 
  //parent.main.document.write(diff+"<br>");
  
  inhalt.scrollTop += diff;
  
  startY = event.clientY;
  
  dragging = event;
  inhalt = null;
}

/************************************************
 * Mausrad scrollen
 *************************************************/

function handle(delta) {
  if (delta < 0) {
    scrolling = true;
    scrollwindow(-delta*20);
    scrolling = false;
  } else {
    scrolling = true;
    scrollwindow(-delta*20);
    scrolling = false;
  }
}

/** Event handler for mouse wheel event.
 */
function scrollWheel(event){
  var delta = 0;
  if (!event)
    event = window.event;
    /* IE/Opera. */
  if(event.wheelDelta) {
    delta = event.wheelDelta / 120;
    /** In Opera 9, delta differs in sign as compared to IE. */
    if (window.opera)
      delta = -delta;
  } else if (event.detail) { /** Mozilla case. */
    /** In Mozilla, sign of delta is different than in IE.
     * Also, delta is multiple of 3. */
    delta = -event.detail / 3;
  }
  /** If delta is nonzero, handle it.
   * Basically, delta is now positive if wheel was scrolled up,
   * and negative, if wheel was scrolled down.
   */
  if (delta)
    handle(delta);
  /** Prevent default actions caused by mouse wheel.
   * That might be ugly, but we handle scrolls somehow
   * anyway, so don't bother here..
   */
  if (event.preventDefault)
    event.preventDefault();
  
  event.returnValue = false;
}

// add event listener cross browser compatible
if(window.addEventListener)
  window.addEventListener('DOMMouseScroll', scrollWheel, false);
else
  window.onmousewheel = document.onmousewheel = scrollWheel;


//
// Sidebar ajax stuff
//

// TODO: The sidebar cannot longer be embedded. We can use relative
// links again and do not need to know the base url any longer :-)

refresh_snapins = null;

// Removes a snapin from the sidebar without reloading anything
function removeSnapin(id, code) {
  var container = document.getElementById(id).parentNode;
  var parent = container.parentNode;
  parent.removeChild(container);
  container = null;
  parent = null;
}

// Updates the contents of a snapin container after get_url
function updateContents(id, code) {
  var obj = document.getElementById(id);
  if(obj) {
    obj.innerHTML = code;
    executeJS(id);
    obj = null;
  }
}

// There may be some javascript code in the html code rendered by
// sidebar.py. Execute it here. This is needed in some browsers.
function executeJS(objId) {
  // Before switching to asynchronous requests this worked in firefox
  // out of the box. Now it seems not to work with ff too. So now
  // executing the javascript manually.
  // if(!isFirefox()) {
  var obj = document.getElementById(objId);
  var aScripts = obj.getElementsByTagName('script');
  for(var i in aScripts) {
    if(aScripts[i].src && aScripts[i].src !== '') {
      var oScr = document.createElement('script');
      oScr.src = aScripts[i].src;
      document.getElementsByTagName("HEAD")[0].appendChild(oScr);
      oScr = null;
    } else {
      try {
    	  eval(aScripts[i].text);
      } catch(e) {alert(aScripts[i].text + "\nError:" + e.message);}
    }
  }
  aScripts = null;
  obj = null;
}

function isFirefox() {
  return navigator.userAgent.indexOf("Firefox") > -1;
}

function get_url(url, handler, id) {
    if (window.XMLHttpRequest) {
        var AJAX = new XMLHttpRequest();
    } else {
        var AJAX = new ActiveXObject("Microsoft.XMLHTTP");
    }
    
    // Dynamic part to prevent caching
    var dyn = "_t="+Date.parse(new Date());
    if(url.indexOf('\?') !== -1) {
        dyn = "&"+dyn;
    } else {
        dyn = "?"+dyn;
    }
    
    if (AJAX) {
        AJAX.open("GET", url + dyn, true);
        if(typeof handler === 'function')
            AJAX.onreadystatechange = function() {
                if (AJAX.readyState == 4) {
                    handler(id, AJAX.responseText);
                }
            }
        AJAX.send(null);
        return true;
    } else {
        return false;
    }
}

function toggle_sidebar_snapin(oH2, url) {
    var childs = oH2.parentNode.parentNode.childNodes;
    for (var i in childs) {
        child = childs[i];
        if (child.tagName == 'DIV' && child.className == 'content') {
            var oContent = child;
            break;
        }
    }
    // FIXME: Does oContent really exist?
    var closed = oContent.style.display == "none";
    if (closed)
        oContent.style.display = "";
    else
        oContent.style.display = "none";
    /* make this persistent -> save */
    get_url(url + (closed ? "open" : "closed")); 
    oContent = null;
    childs = null;
}

function switch_site(switchvar) {
    get_url("switch_site.py?" + switchvar);
    parent.frames[1].location.reload(); /* reload main frame */
}

function sidebar_scheduler() {
    var timestamp = Date.parse(new Date()) / 1000;
    var newcontent = "";
    for (var i in refresh_snapins) { 
        name    = refresh_snapins[i][0];
        refresh = refresh_snapins[i][1];
        if(timestamp % refresh == 0) {
            get_url("sidebar_snapin.py?name=" + name, updateContents, "snapin_" + name);
        }
    }
    setTimeout(function(){sidebar_scheduler();}, 1000);
}

function addBookmark() {
    href = parent.frames[1].location;
    title = parent.frames[1].document.title;
    get_url("add_bookmark.py?title=" + escape(title) + "&href=" + escape(href), updateContents, "snapin_bookmarks");
}

function hilite_icon(oImg, onoff) {
    src = oImg.src;
    if (onoff == 0)
        oImg.src = oImg.src.replace("hi.png", "lo.png");
    else
        oImg.src = oImg.src.replace("lo.png", "hi.png");
}
