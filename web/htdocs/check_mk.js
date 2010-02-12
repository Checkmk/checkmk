function filter_activation(oid)
{
    var selectobject = document.getElementById(oid);
    var usage = selectobject.value;
    var oTd = selectobject.parentNode.parentNode.childNodes[2];
    var pTd = selectobject.parentNode;
    pTd.setAttribute("className", "usage" + usage);
    pTd.setAttribute("class", "usage" + usage); 
    oTd.setAttribute("class", "widget" + usage);
    oTd.setAttribute("className", "widget" + usage);

    var disabled = usage != "hard";
    for (var i in oTd.childNodes) {
	oNode = oTd.childNodes[i];
	if (oNode.nodeName == "INPUT" || oNode.nodeName == "SELECT") {
	    oNode.disabled = disabled;
	}
    }
    

    p = null;
    oTd = null;
    selectobject = null;
}

function toggle_actionform(linkobject, showtext, hidetext)
{
    var table = document.getElementById("actionform");
    var displayed = table.style.display;
    if (displayed == "none") {
	table.style.display = "";
	linkobject.innerHTML = hidetext;
    }
    else {
	table.style.display = "none";
	linkobject.innerHTML = showtext;
    }
}
