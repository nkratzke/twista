from setuptools import setup, find_packages

setup(
    name='Twista',
    version='0.0.4',
    url='https://github.com/nkratzke/twista',
    license='MIT',
    author='Nane Kratzke',
    author_email='nane@nkode.io',
    description='Twitter streaming and analysis',
    scripts=[
        'bin/twista-stream.py',
        'bin/twista-build-graph.py',
        'bin/twista-crawl.py',
        'bin/twisting.py',
    ],
    packages=find_packages(),
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
        "tqdm"
    ]
)
