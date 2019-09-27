var highlight = '#FF4081';
var cy = cytoscape({
    container: document.getElementById('retweet-network'),
    layout: { name: 'random' },
    style: [
        {
            selector: 'node',
            style: {
                'background-color': '#AAAAAA',
                'opacity': 0.5,
            }
        },
        {
            selector: 'node[select = "start"]',
            style: {
                'content': 'data(screen_name)',
                'color': highlight,
                'font-size': 24,
                'background-color': highlight,
                'opacity': 1.0
            }
        },
        {
            selector: 'node.current',
            style: {
                'content': 'data(screen_name)'
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 'data(qty)',
                'line-color': '#CCCCCC',
                'curve-style': 'bezier',
                'target-arrow-shape': 'triangle',
                'target-arrow-color': '#CCCCCC', 
                'opacity': 0.5
            }
        },
        {
            selector: '.outgoing',
            style: {
                'background-color': highlight,
                'line-color': highlight,
                'target-arrow-color': highlight
            }
        },
        {
            selector: '.incoming, .current',
            style: {
                'background-color': 'blue',
                'line-color': 'blue',
                'target-arrow-color': 'blue'
            }
        }
    ],

    elements: {{ elements | safe }}
});
const maxSize = Math.max(...cy.elements('node').map(n => n.indegree(false) + 2 * n.outdegree(false)));
const maxQty = Math.max(...cy.elements('edge').map(e => e.data('qty')));
cy.elements('node').forEach(n => n.css({
    'width': 50 * (n.indegree(false) + 2 * n.outdegree(false)) / maxSize,
    'height': 50 * (n.indegree(false) + 2 * n.outdegree(false)) / maxSize
}));

cy.elements('edge').forEach(e => e.css({'width': Math.max(1, 10 * e.data('qty') / maxQty)}));

cy.layout({
    name: 'cose',
    animate: true,
    delayAnimation: 250,
    randomize: true,
    fit: true,
    edgeElasticity: edge => edge.data('qty') * 32,
    nodeRepulsion: node => node.degree() * 2048,
}).run()

cy.on('mouseover', 'edge', ev => ev.target.toggleClass('current'));
cy.on('mouseout', 'edge', ev => ev.target.toggleClass('current'));
cy.on('click', 'edge', ev => {
    loadText("/retweets/", {
            'source': ev.target.source().id(),
            'target': ev.target.target().id(), 
            'begin': localStorage.getItem('begin'), 
            'end': localStorage.getItem('end')
        }, 
        response => document.getElementById('inspect').innerHTML = response
    );
});

cy.on('mouseover', 'node', ev => {
    ev.target.outgoers().forEach(e => e.toggleClass('outgoing'));
    ev.target.toggleClass('current');
    cy.elements()
        .aStar({ root: "[select = 'start']", goal: ev.target, directed: true })
        .path.forEach(e => e.toggleClass('incoming'));
});
cy.on('mouseout', 'node', ev => {
    ev.target.outgoers().forEach(e => e.toggleClass('outgoing'));
    ev.target.toggleClass('current');
    cy.elements()
        .aStar({ root: "[select = 'start']", goal: ev.target, directed: true })
        .path.forEach(e => e.toggleClass('incoming'));
});
cy.on('click', 'node', ev => {
    loadText("/user/" + ev.target.id() + "/info", { 
            'begin': localStorage.getItem('begin'), 
            'end': localStorage.getItem('end')
        }, 
        response => document.getElementById('inspect').innerHTML = response
    );
});

alert("should work");
