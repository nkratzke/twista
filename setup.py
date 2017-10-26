from setuptools import setup, find_packages

setup(
    name='Twista',
    version='0.2.0',
    url='https://github.com/nkratzke/twista',
    license='MIT',
    author='Nane Kratzke',
    author_email='nane@nkode.io',
    description='Twitter streaming and analysis',
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
        "bs4",
        "requests",
        "tweepy",
        "numpy",
        "python-dateutil",
        "pandas",
        "scipy",
        "matplotlib",
        "html5lib",
        "wordcloud",
        "stop-words",
        "networkx",
        "tqdm",
        "treetaggerwrapper",
        "selenium"
    ]
)
