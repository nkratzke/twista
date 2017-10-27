# Twista
Twista is a Twitter streaming and analysis command line tool suite implemented in Python 3.6. It provides the following core features:

- to __crawl__ HTML pages for Twitter accounts,
- to __recorded__ Tweets (statuses, replies, retweets, replies) for a specified set of screennames,
- to __render__ collected chunks of Tweets into a [NetworkX](https://networkx.github.io/) graph for follow up analysis of observed Twitter interactions,
- and to __query__ the resulting graph.

How to use Twista for recording and analysis of Twitter streams can be found in the [Wiki](wiki).

> Twista has been evaluated recording tweets during the German Federal Election Campaigns of 2017. Over four months Twista recorded 10 GB of data without any operator interaction!
> This dataset is open access and available here: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.835735.svg)](https://doi.org/10.5281/zenodo.835735)
