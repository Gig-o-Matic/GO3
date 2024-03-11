// CODE FOR COMMENTS ON AGENDA PAGE
function show_comment(the_plan) {
    $('#comment-init-'+the_plan).hide();
    $('#comment-row-'+the_plan).show();
    setTimeout(function(){
        $('#comment-'+the_plan).click();
    }, 100);
}

function closed_comment(thing) {
    if ($('#comment-'+thing).text()=='') {
        $('#comment-init-'+thing).show();
        $('#comment-row-'+thing).hide();
    }
}

function init_plan_comments(token) {
    $('.comment-thing').editable({
        emptytext: '<i class="far fa-comment"></i>',
        emptyclass: 'empty-comment',
        mode: 'inline',
        ajaxOptions: { headers: {"X-CSRFToken": token }},
    }).on('hidden', function(e, reason) {
        closed_comment(e.target.getAttribute('data-pk'));
    })
    
}

$(document).ready(function() {
});

$.fn.editableform.template = `\
<form class="form-inline editableform">
    <div class="control-group w-100">
         <div class="d-md-flex justify-content-end align-items-stretch">
            <div class="editable-input d-block flex-shrink-1 w-100 mb-1 mb-md-0"></div>
            <div class="editable-buttons d-block text-right"></div>
        </div>
         <div class="editable-error-block"></div>
    </div> 
</form>`

$.fn.editableform.buttons = `\
<button type="submit" class="editable-submit btn btn-sm btn-primary h-100">ok</button>
<button type="button" class="editable-cancel btn btn-sm btn-secondary h-100 ml-0">cancel</button>`
