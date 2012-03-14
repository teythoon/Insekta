$(function() {
    function register_eventhandler() {
        $('form[name="vmbox_form"]').submit(submit_action);
    }
    
    function submit_action(ev) {
        var action = ev.target.action.value;
        var csrf_token = ev.target.csrfmiddlewaretoken.value;
        var target_url = ev.target.getAttribute('action');
        
        $('#scenario_sidebar').hide();
        $('#vm_spinner').show()
        
        $.post(target_url, {
            'action': action,
            'csrfmiddlewaretoken': csrf_token    
        }, function(result) {
            check_new(target_url, result['task_id'])
        }, 'json');

        ev.preventDefault();
        ev.stopPropagation();
    }

    function check_new(check_url, task_id) {
        setTimeout(function() {
            $.get(check_url, {'task_id': task_id}, function(result, s, xhr) {
                if (xhr.status == 200) {
                    $('#vm_spinner').hide();
                    $('#scenario_sidebar').html(result).show();
                    register_eventhandler()
                } else if (xhr.status == 304) {
                    check_new(check_url, task_id);
                }
            }, 'xhtml');
        }, 1500);
    }
    
    register_eventhandler();

    $(".spoiler").hide();
    $('<a class="reveal_spoiler">show spoiler</a> ').insertBefore('.spoiler');
    
    $("a.reveal_spoiler").click(function(ev) {
        var link = $(ev.target);
        link.next().show();
        link.hide();
    });
});
