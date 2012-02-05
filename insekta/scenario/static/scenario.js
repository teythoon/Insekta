document.addEventListener('DOMContentLoaded', function() {
    function register_eventhandler() {
        var vm_forms = document.getElementsByName('vmbox_form');
        for (var i = 0; i < vm_forms.length; i++) {
            vm_forms[i].addEventListener('submit', submit_action, false);
        }
    }
    
    function submit_action(ev) {
        var action = ev.target.action.value;
        var csrf_token = ev.target.csrfmiddlewaretoken.value;
        var target_url = ev.target.getAttribute('action');
        
        document.getElementById('scenario_sidebar').innerHTML = '';
        document.getElementById('vm_spinner').style.display = 'block';
        
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4) {
                if (xhr.status == 200) {
                    var result = eval('(' + xhr.responseText + ')');
                    check_new(target_url, result['task_id']);
                } else {
                    document.getElementById('scenario_sidebar').innerHTML = 'ERROR';
                }
            }
        }
        xhr.open('POST', target_url, false);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.send('action=' + action + '&csrfmiddlewaretoken=' + csrf_token);

        ev.preventDefault();
        ev.stopPropagation();
    }

    function check_new(check_url, task_id) {
        setTimeout(function() {
            var xhr = new XMLHttpRequest();
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4) {
                    if (xhr.status == 200) {
                        document.getElementById('vm_spinner').style.display = 'none';
                        document.getElementById('scenario-sidebar').innerHTML = xhr.responseText;
                        register_eventhandler();
                    } else if (xhr.status == 304) { // not modified
                        check_new(check_url, task_id);
                    } else {
                        document.getElementById('scenario-sidebar').innerHTML = 'ERROR';
                    }
                }
            }
            xhr.open('GET', check_url + '?task_id=' + task_id, false);
            xhr.send(null);
        }, 1500);
    }
    
    register_eventhandler();
}, false);
