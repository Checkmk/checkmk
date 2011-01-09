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

var browser         = navigator.userAgent.toLowerCase();
var weAreIEF__k     = ((browser.indexOf("msie") != -1) && (browser.indexOf("opera") == -1));
var weAreOpera      = browser.indexOf("opera") != -1;
var weAreFirefox    = browser.indexOf("firefox") != -1 || browser.indexOf("namoroka") != -1;
var contentLocation = null;
if(contentFrameAccessible())
    var contentLocation = parent.frames[1].document.location;

//
// Sidebar styling and scrolling stuff
//

/************************************************
 * Register events
 *************************************************/

// First firefox and then IE
if (window.addEventListener) {
  window.addEventListener("mousemove",     function(e) {
                                             snapinDrag(e);
                                             dragScroll(e);
                                             return false;
                                           }, false);
  window.addEventListener("mousedown",        startDragScroll, false);
  window.addEventListener("mouseup",          stopDragScroll,  false);
  if(weAreFirefox)
    window.addEventListener('DOMMouseScroll', scrollWheel,     false);
  else
    window.addEventListener('mousewheel',     scrollWheel,     false);
} else {
  document.documentElement.onmousemove  = function(e) {
    // snapin drag 'n drop
    snapinDrag(e);
    // drag/drop scrolling
    dragScroll(e);
    return false;
  };
  // drag/drop scrolling
  document.documentElement.onmousedown  = startDragScroll;
  document.documentElement.onmouseup    = stopDragScroll;
  // mousewheel scrolling
  document.documentElement.onmousewheel = scrollWheel;
}

// This ends drag scrolling when moving the mouse out of the sidebar
// frame while performing a drag scroll.
// This is no 100% solution. When moving the mouse out of browser window
// without moving the mouse over the edge elements the dragging is not ended.
function registerEdgeListeners(obj) {
    var edges;
    if (!obj)
        edges = [ parent.frames[1], document.getElementById('side_header'), document.getElementById('side_footer') ];
    else
        edges = [ obj ];

    for(var i in edges) {
        // It is possible to open other domains in the content frame - don't register
        // the event in that case. It is not permitted by most browsers!
        if(!contentFrameAccessible())
            continue;

        if (window.addEventListener)
            edges[i].addEventListener("mousemove", function(e) {
                                                       stopDragScroll(e);
                                                       snapinTerminateDrag(e);
                                                       return false;
                                                   }, false);
        else
            edges[i].onmousemove = function(e) {
                                       stopDragScroll(e);
                                       snapinTerminateDrag(e);
                                       return false;
                                   };
    }
    edges = null;
}

/************************************************
 * snapin drag/drop code
 *************************************************/

var snapinDragging = false;
var snapinOffset   = [ 0, 0 ];
var snapinStartPos = [ 0, 0 ];
var snapinScrollTop = 0;

function getButton(event) {
  if (event.which == null)
    /* IE case */
    return (event.button < 2) ? "LEFT" : ((event.button == 4) ? "MIDDLE" : "RIGHT");
  else
    /* All others */
    return (event.which < 2) ? "LEFT" : ((event.which == 2) ? "MIDDLE" : "RIGHT");
}

function getTarget(event) {
  return event.target ? event.target : event.srcElement;
}

function snapinStartDrag(event) {
  if (!event)
    event = window.event;

  var target = getTarget(event);
  var button = getButton(event);

  // Skip calls when already dragging or other button than left mouse
  if (snapinDragging !== false || button != 'LEFT' || target.tagName != 'DIV')
    return true;

  if (event.stopPropagation)
    event.stopPropagation();
  event.cancelBubble = true;
  
  snapinDragging = target.parentNode;

  // Save relative offset of the mouse to the snapin title to prevent flipping on drag start
  snapinOffset   = [ event.clientY - target.parentNode.offsetTop, 
                     event.clientX - target.parentNode.offsetLeft ];
  snapinStartPos = [ event.clientY, event.clientX ];
  snapinScrollTop = document.getElementById('side_content').scrollTop;
  
  // Disable the default events for all the different browsers
  if (event.preventDefault)
    event.preventDefault();
  else
    event.returnValue = false;
  return false;
}

function snapinDrag(event) {
  if (!event)
    event = window.event;

  if (snapinDragging === false)
    return true;

  // Is the mouse placed of the title bar of the snapin?
  // It can move e.g. if the scroll wheel is wheeled during dragging...

  // Drag the snapin
  snapinDragging.style.position = 'absolute';
  var newTop = event.clientY  - snapinOffset[0] - snapinScrollTop;
  /*if (weAreIEF__k) 
      newTop += document.getElementById('side_content').scrollTop;*/
  snapinDragging.style.top      = newTop + 'px';
  snapinDragging.style.left     = (event.clientX - snapinOffset[1]) + 'px';
  snapinDragging.style.width    = '175px';
  snapinDragging.style.zIndex   = 200;

  // Refresh the drop marker
  removeSnapinDragIndicator();
  
  var line = document.createElement('div');
  line.setAttribute('id', 'snapinDragIndicator');
  line.style.height          = '3px';
  line.style.lineHeight      = '1px';
  line.style.fontSize        = '1px';
  line.style.width           = '250px';
  line.style.backgroundColor = '#fff';
  line.style.margin          = '1px 0px 0px 5px';
  var o = getSnapinTargetPos();
  if (o != null) {
    snapinAddBefore(o.parentNode, o, line);
    o = null;
  } else {
    snapinAddBefore(snapinDragging.parentNode, null, line);
  }
  line = null;
	return true;
}

function snapinAddBefore(par, o, add) {
  if (o != null) {
    par.insertBefore(add, o);
    o = null;
  } else {
    par.appendChild(add);
  }
  add = null;
}

function removeSnapinDragIndicator() {
  var o = document.getElementById('snapinDragIndicator');
  if (o) {
    o.parentNode.removeChild(o);
    o = null;
  }
}

function snapinDrop(event, targetpos) {
  if (snapinDragging == false)
    return true;

  // Reset properties
  snapinDragging.style.top      = '';
  snapinDragging.style.left     = '';
  snapinDragging.style.position = '';

  // Catch quick clicks without movement on the title bar
  // Don't reposition the object in this case.
  if (snapinStartPos[0] == event.clientY && snapinStartPos[1] == event.clientX) {
    if (event.preventDefault)
      event.preventDefault();
    if (event.stopPropagation)
      event.stopPropagation();
    event.returnValue = false;
    return false;
  }
  
  var par = snapinDragging.parentNode;
  par.removeChild(snapinDragging);
  snapinAddBefore(par, targetpos, snapinDragging);

  // Now send the new information to the backend
  var thisId = snapinDragging.id.replace('snapin_container_', '');

  var before = '';
  if (targetpos != null)
    before = '&before=' + targetpos.id.replace('snapin_container_', '');
  get_url('sidebar_move_snapin.py?name=' + thisId + before);
  thisId = null;
  targetpos = null;
}

function snapinTerminateDrag() {
  if(snapinDragging == false)
    return true;
	removeSnapinDragIndicator();
  // Reset properties
  snapinDragging.style.top      = '';
  snapinDragging.style.left     = '';
  snapinDragging.style.position = '';
  snapinDragging = false;
}

function snapinStopDrag(event) {
  if (!event)
    event = window.event;
  
  removeSnapinDragIndicator();
  snapinDrop(event, getSnapinTargetPos());
  snapinDragging = false;
}

function getDivChildNodes(node) {
  var children = [];
  for(var i in node.childNodes)
    if(node.childNodes[i].tagName === 'DIV')
      children.push(node.childNodes[i]);
  return children;
}

function getSnapinList() {
  if (snapinDragging === false)
    return true;
  
  var l = [];
  var childs = getDivChildNodes(snapinDragging.parentNode);
  for(var i in childs) {
    var child = childs[i];
    // Skip
    // - non snapin objects
    // - currently dragged object
    if (child.id && child.id.substr(0, 7) == 'snapin_' && child.id != snapinDragging.id)
      l.push(child);
  }

  return l;
}

function getSnapinCoords(obj) {
  var snapinTop = snapinDragging.offsetTop + document.getElementById('side_content').scrollTop;
  
  var bottomOffset = obj.offsetTop + obj.clientHeight - snapinTop;
  if (bottomOffset < 0)
    bottomOffset = -bottomOffset;
      
  var topOffset = obj.offsetTop - snapinTop;
  if (topOffset < 0)
    topOffset = -topOffset;
      
  var offset = topOffset;
  var corner = 0;
  if (bottomOffset < topOffset) {
    offset = bottomOffset
    corner = 1;
  }

  return [ bottomOffset, topOffset, offset, corner ];
}

function getSnapinTargetPos() {
  var snapinTop = snapinDragging.offsetTop;
  var childs = getSnapinList();
  var objId = -1;
  var objCorner = -1;

  // Find the nearest snapin to current left/top corner of
  // the currently dragged snapin
  for(var i in childs) {
    var child = childs[i];

    if (!child.id || child.id.substr(0, 7) != 'snapin_' || child.id == snapinDragging.id)
      continue;

    // Initialize with the first snapin in the list
    if (objId === -1) {
      objId = i;
      var coords = getSnapinCoords(child)
      objCorner = coords[3]; 
      continue;
    }

    // First check which corner is closer. Upper left or
    // the bottom left.
    var curCoords = getSnapinCoords(childs[objId]);
    var newCoords = getSnapinCoords(child);

    // Is the upper left corner closer?
    if (newCoords[2] < curCoords[2]) {
      objCorner = newCoords[3];
      objId = i;
    }
  }

  // Is the dragged snapin dragged above the first one?
  if (objId == 0 && objCorner == 0)
      return childs[0];
  else
      return childs[(parseInt(objId)+1)];
}

/************************************************
 * misc sidebar stuff
 *************************************************/

// Checks if the sidebar can access the content frame. It might be denied
// by the browser since it blocks cross domain access.
function contentFrameAccessible() {
    try {
        var d = parent.frames[1].document;
        d = null;
        return true;
    } catch (e) {
        return false;
    }
}

function debug(s) {
  window.parent.frames[1].document.write(s+'<br />');
}

function pageHeight() {
  var h;
  
  if (window.innerHeight !== null && typeof window.innerHeight !== 'undefined' && window.innerHeight !== 0)
    h = window.innerHeight;
  else if (document.documentElement && document.documentElement.clientHeight)
    h = document.documentElement.clientHeight;
  else if (document.body !== null)
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

	// Don't handle zero heights
	if(height == 0)
		return;

  oContent.style.height = (height - oHeader.clientHeight - oFooter.clientHeight - 5) + 'px';

	oFooter = null;
	oContent = null;
	oHeader = null;
}

var scrolling = true;

function scrollwindow(speed){
  var c = document.getElementById('side_content');
  
  if (scrolling) {
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

function startDragScroll(event) {
  if (!event)
    event = window.event;

  var target = getTarget(event);
  var button = getButton(event);
  
  // Evtl. auch nur mit Shift Taste: (e.button == 0 && (e["shiftKey"])
  if (dragging === false && button == 'LEFT'
      && target.tagName != 'A'
      && target.tagName != 'INPUT'
      && !(target.tagName == 'DIV' && target.className == 'heading')) {
    if (event.preventDefault)
      event.preventDefault();
    if (event.stopPropagation)
      event.stopPropagation();
    event.returnValue = false;
    
    dragging = event;
    startY = event.clientY;
    startScroll = document.getElementById('side_content').scrollTop;

    return false;
  }
  return true;
}

function stopDragScroll(event){ 
  dragging = false;
}

function dragScroll(event) {
  if (!event)
    event = window.event;
  
  if (dragging === false)
    return true;
  
  if (event.preventDefault)
    event.preventDefault();
  event.returnValue = false;
  
  if (event.stopPropagation)
    event.stopPropagation();
  event.cancelBubble = true;
  
  var inhalt = document.getElementById('side_content');
  var diff = startY - event.clientY;
  
  inhalt.scrollTop += diff;

	// Opera does not fire onunload event which is used to store the scroll
	// position. So call the store function manually here.
  if(weAreOpera)
    storeScrollPos();
  
  startY = event.clientY;
  
  dragging = event;
  inhalt = null;

  return false;
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

  if (event.wheelDelta)
    delta = event.wheelDelta / 120;
  else if (event.detail)
    delta = -event.detail / 3;

  if (delta)
    handle(delta);

	// Opera does not fire onunload event which is used to store the scroll
	// position. So call the store function manually here.
  if(weAreOpera)
    storeScrollPos();

  if (event.preventDefault)
    event.preventDefault();
  else
    event.returnValue = false;
  return false;
}


//
// Sidebar ajax stuff
//

// TODO: The sidebar cannot longer be embedded. We can use relative
// links again and do not need to know the base url any longer :-)

refresh_snapins = null;

// Removes a snapin from the sidebar without reloading anything
function removeSnapin(id, code) {
  var container = document.getElementById(id).parentNode;
  var myparent = container.parentNode;
  myparent.removeChild(container);

  // reload main frame if it is just displaying the "add snapin" page
  var href = escape(parent.frames[1].location);
  if (href.indexOf("sidebar_add_snapin.py") > -1)
      parent.frames[1].location.reload();

  href = null;
  container = null;
  myparent = null;
}

// Updates the contents of a snapin container after get_url
function updateContents(id, code) {
  var obj = document.getElementById(id);
  if (obj) {
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
  // if (!isFirefox()) {
  var obj = document.getElementById(objId);
  var aScripts = obj.getElementsByTagName('script');
  for(var i in aScripts) {
    if (aScripts[i].src && aScripts[i].src !== '') {
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

function toggle_sidebar_snapin(oH2, url) {
    var childs = oH2.parentNode.parentNode.childNodes;
    for (var i in childs) {
        child = childs[i];
        if (child.tagName == 'DIV' && child.className == 'content')
            var oContent = child;
        else if (child.tagName == 'DIV' && (child.className == 'head open' || child.className == "head closed"))
            var oHead = child;
        else if (child.tagName == 'DIV' && child.className == 'foot')
            var oFoot = child;
    }
    // FIXME: Does oContent really exist?
    var closed = oContent.style.display == "none";
    if (closed) {
        oContent.style.display = "";
        oFoot.style.display = "";
        oHead.className = "head open";
    }
    else {
        oContent.style.display = "none";
        oFoot.style.display = "none";
        oHead.className = "head closed";
    }
    /* make this persistent -> save */
    get_url(url + (closed ? "open" : "closed")); 
    oContent = null;
    oHead = null;
    oFoot = null;
    childs = null;
}

function reload_main_plus_sidebar(id, code) {
    parent.frames[1].location.reload(); /* reload main frame */
    parent.frames[0].location.reload(); /* reload side bar */
}

function switch_site(switchvar) {
    get_url("switch_site.py?" + switchvar, reload_main_plus_sidebar, null);
    /* After the site switch has been done, everything must be reloaded since
       everything is affected by the switch */
}

function sidebar_scheduler() {
    var timestamp = Date.parse(new Date()) / 1000;
    var newcontent = "";
    for (var i in refresh_snapins) { 
        var name    = refresh_snapins[i][0];
        var refresh = refresh_snapins[i][1];
        var url = "sidebar_snapin.py?name=" + name;
        if(refresh_snapins[i][2] != '')
            url = refresh_snapins[i][2];

        if (timestamp % refresh == 0) {
            get_url(url, updateContents, "snapin_" + name);
        }
    }
    // Detect page changes and re-register the mousemove event handler
    // in the content frame. another bad hack ... narf
    if (contentFrameAccessible() && contentLocation != parent.frames[1].document.location) {
        registerEdgeListeners(parent.frames[1]);
        contentLocation = parent.frames[1].document.location;
    }
    setTimeout(function(){sidebar_scheduler();}, 1000);
}

function addBookmark() {
    href = parent.frames[1].location;
    title = parent.frames[1].document.title;
    get_url("add_bookmark.py?title=" + escape(title) + "&href=" + escape(href), updateContents, "snapin_bookmarks");
}

function toggle_folder(o, folderId) {
    var par = o.parentNode;
    var next = null;
    var one_more = false;
    var img = null;

    for (var i in par.childNodes) {
        var child = par.childNodes[i];
        if (one_more && child.nodeName == "DIV") {
            next = child;
            break;
        }
        if (child == o) 
            one_more = true;
    }

    for (var i in o.childNodes) {
        var child = o.childNodes[i];
        if (child.nodeName == "IMG") {
            img = child;
            break;
        }
    }

    if (next) {
        if (next.style.display == "none") {
            next.style.display = "";
            if (img) 
                img.src = "images/link_folder_open.gif";
            get_url('customlink_openclose.py?name=' + escape(folderId) + '&state=on');
        } else {
            next.style.display = "none";
            if (img) 
                img.src = "images/link_folder.gif";
            get_url('customlink_openclose.py?name=' + escape(folderId) + '&state=off');
        }
    }

    child = null;
    par = null;
    next = null;
    img = null;
}

/************************************************
 * Save/Restore scroll position
 *************************************************/

function setCookie(cookieName, value,expiredays) {
    var exdate = new Date();
    exdate.setDate(exdate.getDate() + expiredays);
    document.cookie = cookieName + "=" + escape(value) +
        ((expiredays == null) ? "" : ";expires=" + exdate.toUTCString());
}

function getCookie(cookieName) {
    if(document.cookie.length == 0)
        return null;

    var cookieStart = document.cookie.indexOf(cookieName + "=");
    if(cookieStart == -1)
        return null;
    
    cookieStart = cookieStart + cookieName.length + 1;
    var cookieEnd = document.cookie.indexOf(";", cookieStart);
    if(cookieEnd == -1)
        cookieEnd = document.cookie.length;
    return unescape(document.cookie.substring(cookieStart, cookieEnd));
}

function initScrollPos() {
    var scrollPos = getCookie('sidebarScrollPos');
    if(!scrollPos)
        scrollPos = 0;
    document.getElementById('side_content').scrollTop = scrollPos;
}

function storeScrollPos() {
    setCookie('sidebarScrollPos', document.getElementById('side_content').scrollTop, null);
}
