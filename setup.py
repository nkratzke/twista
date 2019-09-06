from setuptools import setup, find_packages
import twista

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name=twista.name,
    version=twista.VERSION,
    url='https://github.com/nkratzke/twista',
    license='MIT',
    author='Nane Kratzke',
    author_email='nane.kratzke@th-luebeck.de',
    description='Twitter streaming and graph-based analysis framework',
    long_description_content_type="text/markdown",
    long_description=long_description,
    python_requires=">=3.6,<4.0",
    scripts=[
        'bin/twista',
        # 'bin/twista-navigator.py'
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "certifi",
        "click             >= 7.0,  < 8.0",
        "tweepy            >= 3.5,  < 4.0",
        "python-dateutil   >= 2.6,  < 3.0",
        "tqdm              >= 4.35, < 5.0",
        "neo4j             >= 1.7,  < 2.0",
        "termcolor         >= 1.1,  < 1.2",
        "jupyterlab        >= 1.1,  < 2.0",
        "matplotlib        >= 3.1,  < 4.0",
        "py2neo            >= 4.3,  < 5.0",
        "flask             >= 1.1,  < 1.2"
    ]
)
