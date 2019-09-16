
function loadJson(url, callback) {
    var xmlhttp = new XMLHttpRequest();

    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            callback(JSON.parse(this.responseText));
        }
    };
    xmlhttp.open("GET", url, true);
    xmlhttp.send();
}

function load(url, params, id) {
    document.getElementById(id).innerHTML = '<div class="mdl-spinner mdl-js-spinner is-active"></div>'
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            document.getElementById(id).innerHTML = this.responseText;
        }
    };
    xmlhttp.open("GET", url + "?" + buildURLQuery(params), true);
    xmlhttp.send();
}

function buildURLQuery(map) {
    return Object.entries(map)
                 .map(pair => pair.map(encodeURIComponent).join('='))
                 .join('&');
}

function filterHandler() {
    console.log("filterHandler");
    // Stores filter settings in localstorage
    document.querySelectorAll("#filter input").forEach(i => i.addEventListener("change", () => {
        console.log("Filter change ... ")
        localStorage.setItem("searchterm", document.querySelector("#filter #searchterm").value);
        localStorage.setItem("entity", document.querySelector("#filter #tweets").checked ? "tweet" : "user");
        localStorage.setItem("begin", document.querySelector("#filter #begin").value);
        localStorage.setItem("end", document.querySelector("#filter #end").value);

        document.querySelectorAll("a.filtered").forEach(link => {
            link.setAttribute('href', link.getAttribute('base') + "?" + buildURLQuery({
                'searchterm': localStorage.getItem("searchterm") || "",
                'entity': localStorage.getItem("entity") == "tweet" ? "tweet" : "user",
                'begin': localStorage.getItem("begin") || "",
                'end': localStorage.getItem("end") || "",
            }));
        });
    }));
}

function refreshFilter() {
    document.querySelectorAll("a.filtered").forEach(link => {
        link.setAttribute('base', link.getAttribute('href'));
        link.setAttribute('href', link.getAttribute('base') + "?" + buildURLQuery({
            'searchterm': localStorage.getItem("searchterm") || "",
            'entity': localStorage.getItem("entity") == "tweet" ? "tweet" : "user",
            'begin': localStorage.getItem("begin") || "",
            'end': localStorage.getItem("end") || "",
        }));
    });
    document.querySelector("#filter #searchterm").value = localStorage.getItem('searchterm');
    document.querySelector("#filter #users").checked = localStorage.getItem('entity') == "user";
    document.querySelector("#filter #tweets").checked = !document.querySelector("#filter #users").checked;
    document.querySelector("#filter #begin").value = localStorage.getItem('begin');
    document.querySelector("#filter #end").value = localStorage.getItem('end');
}