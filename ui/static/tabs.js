
window.onload=function() {
  // get tab container
    var container = document.getElementById("tabContainer");
    var tabcon = document.getElementById("tabscontent");
        //alert(tabcon.childNodes.item(1));
    // set current tab
    var navitem = document.getElementById("tabHeader_1");
    //store which tab we are on
    var ident = navitem.id.split("_")[1];
    navitem.parentNode.setAttribute("data-current",ident);
    //set current tab with class of activetabheader
    navitem.setAttribute("class","tabActiveHeader");

    //hide two tab contents we don't need
     var pages = tabcon.getElementsByTagName("div");
        for (var i = 1; i < pages.length; i++) {
         pages.item(i).style.display="none";
        };

    //this adds click event to tabs
    var tabs = container.getElementsByTagName("li");
    for (var a = 0; a < tabs.length; a++) {
      tabs[a].onclick=displayPage;
    }
}

// on click of one of tabs
function displayPage() {
  var current = this.parentNode.getAttribute("data-current");
  //remove class of activetabheader and hide old contents
  document.getElementById("tabHeader_" + current).removeAttribute("class");
  document.getElementById("tabpage_" + current).style.display="none";

  var ident = this.id.split("_")[1];
    console.log(ident)
  //add class of activetabheader to new active tab and show contents
  this.setAttribute("class","tabActiveHeader");
  document.getElementById("tabpage_" + ident).style.display="block";
  this.parentNode.setAttribute("data-current",ident);
}
