
function save_as_default(el, field, value) {

    $.ajax({
        'url': "?action=save_field_as_default",
        'type': "POST",
        'data': {
            field: field,
            value: value
        },
        beforeSend: function( xhr ) {
            function getCookie(name) {
                var cookieValue = null;
                if (document.cookie && document.cookie != '') {
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {
                        var cookie = jQuery.trim(cookies[i]);
                        // Does this cookie string begin with the name we want?
                        if (cookie.substring(0, name.length + 1) == (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }
            var csrfCookieName = window.csrfCookieName || 'csrf';
            xhr.setRequestHeader("X-CSRFToken", getCookie(csrfCookieName));
            el.fadeOut(200);
        }
    }).done(function(data){
        el.find('i').removeClass('icon-lock').addClass('icon-checkmark');
        el.fadeIn(200);
    });
}

function init_action_buttons(container) {
    container.find(".project-field[data-field]").each(function(){
        var action_button = $("<button>")
                .attr('type', 'button')
                .attr('title', SAVE_AS_DEFAULT_BUTTON_MSG)
                .attr('data-placement', 'right')
                .addClass('btn-link btn-sm')
                .addClass('save-as-default')
                .html($('<i>').addClass('icon-lock'));
        $(this).after(action_button);
    });
    $('button[title]').tooltip();
}

function load_issue_form() {
    var spinner = new Spinner().spin();

    $.ajax({
        'url': "?form=1",
        beforeSend: function( xhr ) {
            $(".form-fields").html(spinner.el);
            $(".spinner").css('left', '50%');
        }
    }).done(function(data){
        var container = $(".form-fields");
        var form = $("#create-issue .form-fields", data);
        container.html(form);
        container.find("select").addClass('span3').select2();
        init_action_buttons(container);
    });
}

$(function(){
    var container = $("#create-issue");

    container.delegate(".save-as-default", "click", function(){
        var field = $(this).parents('.controls').find('.project-field[data-field]');
        save_as_default($(this), field.data('field'), String(field.val()));
    });

    init_action_buttons(container);

    function format(state) {
        return "<b>" + state.id +"</b> " + state.summary + " (" + state.state + ")"
    }

    $("#id_issue").select2({
        minimumInputLength: 0,
        ajax: {
            url: "?action=project_issues",
            quietMillis: 100,
            type: 'post',
            dataType: 'json',
            data: function (term, page) {
                return {
                    q: term,
                    page_limit: 15,
                    page: page
                };
            },
            results: function (data, page) {
                return {results: data.issues, more: data.more};
            }
        },
        formatResult: format,
        formatSelection: format
    });
});