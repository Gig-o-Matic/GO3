$(document).ready(function() {
    var bgs = new Array();
    bgs[0] = 'url(/static/images/tuba.png)';
    bgs[1] = 'url(/static/images/bone.png)';
    bgs[2] = 'url(/static/images/tpt.png)';
    $(".landingwrap").css('background-image',bgs[Math.floor(Math.random()*bgs.length)]);
});
