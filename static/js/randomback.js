$(document).ready(function() {
    var bgs = new Array();
    bgs[0] = 'url(/static/images/updrum.png)';
    bgs[1] = 'url(/static/images/tambo.png)';
    bgs[2] = 'url(/static/images/weird-o-phone.png)';
    $(".landingwrap").css('background-image',bgs[Math.floor(Math.random()*bgs.length)]);
});
