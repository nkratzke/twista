from setuptools import setup, find_packages

setup(
    name='Twista',
    version='0.2.2',
    url='https://github.com/nkratzke/twista',
    license='MIT',
    author='Nane Kratzke',
    author_email='nane@nkode.io',
    description='Twitter streaming and analysis',
    python_requires=">=3.6,<3.7",
    scripts=[
        'bin/twista-record.py',
        'bin/twista-build-graph.py',
        'bin/twista-enrich-graph.py',
        'bin/twista-crawl.py',
        'bin/twisting.py',
    ],
    packages=find_packages(),
    data_files=[
       ('twista', ['twista/data/SentiWS_v1.8c_Negative.txt', 'twista/data/SentiWS_v1.8c_Positive.txt'])
    ],
    install_requires=[
        "beautifulsoup4    >= 4.6,  < 4.7",
        "requests          >= 2.18, < 2.19",
        "tweepy            >= 3.5,  < 3.6",
        "numpy             >= 1.13, < 1.14",
        "python-dateutil   >= 2.6,  < 2.7",
        "matplotlib        >= 2.1,  < 2.2",
        "wordcloud         >= 1.3,  < 1.4",
        "networkx          >= 2.0,  < 2.1",
        "tqdm              >= 4.19, < 4.20",
        "treetaggerwrapper >= 2.2,  < 2.3",
        "gensim            >= 3.0,  < 3.1",
        "newspaper3k       >= 0.2,  < 0.3"
    ]
)
