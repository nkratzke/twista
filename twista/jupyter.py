import nbformat as nbf

graph_connect = """
import json
from py2neo import Graph

conf = json.load(open('%s'))
graph = Graph(conf['neo4j_url'], user=conf['neo4j_usr'], password=conf['neo4j_pwd'])
""".strip()

cypher_example = """
import matplotlib.pyplot as plt

queries = [
    { 
        "title": "Distribution of node types",
        "query": "MATCH (n) RETURN labels(n) as category, count(n) AS n ORDER BY n DESCENDING LIMIT 10"
    },
    {
        "title": "Distribution of Tweet subtypes",
        "query": "MATCH (n:Tweet) RETURN n.type as category, count(n) AS n ORDER BY n DESCENDING",
    },
    {
        "title": "Distribution of edge types",
        "query": "MATCH () -[r]-> () RETURN type(r) as category, count (r) AS n ORDER BY n DESCENDING",
    },
    {
        "title": "TOP 10 of mosted retweeted users",
        "query": "MATCH (n:User) -[:POSTS]-> (t:Tweet) <-[rts:REFERS_TO]- (:Tweet{type:'retweet'}) RETURN n.screen_name AS category, count(rts) AS n ORDER BY n DESCENDING LIMIT 10"
    },
    {
        "title": "TOP 10 of mosted retweeting users",
        "query": "MATCH (n:User) -[:POSTS]-> (t:Tweet{type:'retweet'}) RETURN n.screen_name AS category, count(t) AS n ORDER BY n DESCENDING LIMIT 10"
    },
    {
        "title": "TOP 10 of most replying users",
        "query": "MATCH (u:User) -[:POSTS]-> (r:Tweet{type: 'reply'}) RETURN u.screen_name AS category, count(r) AS n ORDER BY n DESCENDING LIMIT 10"
    },
    {
        "title": "TOP 10 of most used tags",
        "query": "MATCH (t:Tweet) -[r:HAS_TAG]-> (tag:Tag) RETURN tag.id AS category, COUNT(r) AS n ORDER BY n DESCENDING LIMIT 10"
    },
    {
        "title": "TOP 10 of most retweeted urls",
        "query": "MATCH (t:Tweet{type: 'retweet'}) -[r:HAS_URL]-> (u:Url) RETURN u.id AS category, COUNT(t) AS n ORDER BY n DESCENDING LIMIT 10"
    },
    {
        "title": "TOP 10 of user locations",
        "query": "MATCH (u:User) WHERE u.location IS NOT NULL RETURN u.location AS category, count(u) AS n ORDER BY n DESCENDING LIMIT 10"
    }
]

for q in queries:
    data = graph.run(q['query']).data()
    category = [d['category'] for d in data]
    values = [d['n'] for d in data]
    plt.title(q['title'])
    plt.pie(values, labels=category, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.show()
""".strip()

def notebook(config):
    nb = nbf.v4.new_notebook()
    nb['cells'] = [
        nbf.v4.new_markdown_cell("# Graph analysis"),
        nbf.v4.new_markdown_cell(
            "Twista generated this notebook for demonstrating purposes. "
            "Copy and/or adapt it to your specfic analysis requirements. "
        ),
        nbf.v4.new_code_cell(graph_connect % config),
        nbf.v4.new_markdown_cell("## Graph query examples"),
        nbf.v4.new_markdown_cell(
            "The following queries are just some example Cypher queries "
            "demonstrating how to query the graph and how "
            "visualizing observable quantitative aspects. "
            "\n"
            "You might find the following links usefull:\n"
            "\n"
            "- [Introduction to Cypher](https://neo4j.com/developer/cypher-query-language/)\n"
            "- [Introduction to matplotlib](https://matplotlib.org/3.1.1/tutorials/introductory/pyplot.html)"
            "- [Twista Wiki]()"
        ),
        nbf.v4.new_code_cell(cypher_example)
    ]
    return nb