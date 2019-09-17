
function loadJson(url, params, callback) {
    var xmlhttp = new XMLHttpRequest();

    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            callback(JSON.parse(this.responseText));
        }
    };
    xmlhttp.open("GET", url + "?" + buildURLQuery(params), true);
    xmlhttp.send();
}

function loadText(url, params, callback) {
    var xmlhttp = new XMLHttpRequest();

    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            callback(this.responseText);
            refreshFilter();
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

function plot(into, data) {
    into.querySelector('.mdl-spinner').remove();
    var div = document.createElement('div');
    into.prepend(div);
    Plotly.newPlot(div, data, { }, { 
        'responsive': true 
    });
}

function observeFilter() {
    document.querySelector("#filter #begin").value = localStorage.getItem("begin") || "";
    document.querySelector("#filter #end").value = localStorage.getItem("end") || "";
    document.querySelectorAll("#filter #begin, #filter #end").forEach(e => e.addEventListener('change', () => {
        localStorage.setItem('begin', document.querySelector("#filter #begin").value || "");
        localStorage.setItem('end', document.querySelector("#filter #end").value || "");
        refreshFilter();
    }));
}

function refreshFilter() {
    document.querySelectorAll("a.filtered").forEach(link => {
        const url = new URL(link.getAttribute('href'), window.location.origin)
        link.setAttribute('href', url.origin + url.pathname + "?" + buildURLQuery({
            'begin': localStorage.getItem("begin") || "",
            'end': localStorage.getItem("end") || "",
        }));
    });
}