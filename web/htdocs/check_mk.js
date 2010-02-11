function filter_activation(oid)
{
    var selectobject = document.getElementById(oid);
    var disabled = selectobject.value != "hard"; 
    var oTd = selectobject.parentNode.parentNode.childNodes[2];
    if (disabled) {
	oTd.setAttribute("class", "widget_off");
	oTd.setAttribute("className", "widgetoff");
	oTd.style.color = "#bbb";
    }
    else {
	oTd.setAttribute("class", "widget");
	oTd.setAttribute("className", "widget")
	oTd.style.color = "#000";
    }

    for (var i in oTd.childNodes) {
	oNode = oTd.childNodes[i];
	if (oNode.nodeName == "INPUT" || oNode.nodeName == "SELECT") {
	    oNode.disabled = disabled;
	}
    }
    oTd = null;
    selectobject = null;
}
