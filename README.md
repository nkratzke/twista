# Twista
Twista is a Twitter streaming and analysis command line tool suite implemented in Python 3. It provides the following core features:

- to __record__ Tweets (statuses, replies, retweets, replies) from the public Twitter streaming API in a standardized way,
- to __import__ collected chunks of Tweets into a [Neo4j](https://neo4j.com/) graph database for analysis.
- The graph database can be used for analysis. We recommand to make use of tools like [Jupyter](https://jupyter.org).
  Twista provides integrated support for Jupyter. Try the `twista lab` command to start Jupyter with the current config file.

## Installation

Twista is hosted on [PyPi](). Therefore, it can be easily installed:

```
pip3 install twista
```

Type

```
$ twista
```

to get an overview of existing Twista commands.

```
Usage: twista [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  import     Imports Twitter records into a Neo4j graph database
  init       Initializes a directory to be used with Twista
  lab        Starts Jupyter lab for analysis
  navigator  Starts the Twista navigator app
  record     Records a Twitter stream
  stop       Stops the Neo4j database
  version    Reports the version of Twista
```

We recommend to study the [Wiki]() on how to record and analyze public Twitter streams using Twista and graph databases.

## Twista passed its acid-tests

> Twista (0.3.0) is been used to record a sample of the complete German Twitter stream since April 2019.
> This dataset is open access, updated monthly, and available here: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.2783954.svg)](https://doi.org/10.5281/zenodo.2783954)

> Twista (0.2.0) has been evaluated recording tweets during the German Federal Election Campaigns of 2017. Over four months Twista recorded 10 GB of data without any operator interaction!
> This dataset is open access and available here: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.835735.svg)](https://doi.org/10.5281/zenodo.835735)
