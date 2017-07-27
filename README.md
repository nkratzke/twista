# Twista
Twista is a Twitter streaming and analysis command line tool suite implemented in Python 3.6.

It provides the following command line tools:

- __twista-crawl.py__ to crawl HTML pages for Twitter accounts by searching for &lt;a href='http://twitter.com/username' &gt; User name &lt;a&gt; HTML elements.
- __twista-stream.py__ to collect Tweets (statuses, replies, retweets, replies) for a specified set of screennames.
- __twista-build-graph.py__ to process collected chunks of Tweets and transform them into a [NetworkX](https://networkx.github.io/) graph. This graph is used for follow up analysis of observed Twitter interactions.

More detailled usage information will be provided here. Stay tuned.
