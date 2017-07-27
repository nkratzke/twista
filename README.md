# Twista
Twista is a Twitter streaming and analysis command line tool suite implemented in Python 3.6.

It provides the following command line tools:

- `twista-crawl.py` to crawl HTML pages for Twitter accounts by searching for `<a href='http://twitter.com/username'>User name</a>` HTML elements.
- `twista-stream.py` to collect Tweets (statuses, replies, retweets, replies) for a specified set of screennames.
- `twista-build-graph.py` to process collected chunks of Tweets and transform them into a [NetworkX](https://networkx.github.io/) graph. This graph is used for follow up analysis of observed Twitter interactions.

More detailled usage information will be provided here. Stay tuned.
