from pkg_resources import resource_filename
from twista.analysis import TwistaList
import treetaggerwrapper

TAGGER = {
    'de': treetaggerwrapper.TreeTagger(TAGLANG='de'),
    'en': treetaggerwrapper.TreeTagger(TAGLANG='en')
}


NOUN_TAGS = {
    'de': ['NE', 'NA', 'NN'],
    'en': ['NN', 'NNS', 'NP', 'NPS']
}


'''
Loads german sentiments as mapping from lemma to sentiment value (-1.0, ..., 1.0).
'''
def _german_sentiments():
    sentiments = {}
    files = [
        resource_filename('twista', 'SentiWS_v1.8c_Negative.txt'),
        resource_filename('twista', 'SentiWS_v1.8c_Positive.txt'),
    ]
    for file in files:
        text = open(file).read()
        for line in text.split("\n"):
            if not line:
                continue
            data = line.split()
            lemma = data[0].split('|')[0]
            priority = float(data[1])
            sentiments[lemma] = priority
    return sentiments


SENTIMENTS = {
    'de': _german_sentiments()
}


'''
Calculates the mean polarity of a list of lemmas.
:param lemmas List of lemmas (String)
:param lang Language (ISO-code, e.g. 'en' for English, 'de' for German)
:return Float (mean polarity value of all lemmas), None is returned if no polarity value can be calculated
'''
def polarity(lemmas, lang='de'):
    if not lemmas:
        return None

    if lang not in SENTIMENTS:
        return None

    sentiments = SENTIMENTS[lang]
    considered_lemmas = [l for l in lemmas if l in sentiments]

    if not considered_lemmas:
        return (0, 0)

    positives = [sentiments[lemma] for lemma in considered_lemmas if sentiments[lemma] > 0]
    if not positives:
        positives = [0]

    negatives = [sentiments[lemma] for lemma in considered_lemmas if sentiments[lemma] < 0]

    if not negatives:
        negatives = [0]

    return (sum(positives), sum(negatives))


'''
Performs a part-of-speech-tagging using the POS tagger TreeTagger
(http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/).
:param text String to POS tags
:return list of POS tags
'''
def pos_tagging(text, lang='de'):
    if lang not in TAGGER:
        return []
    tags = treetaggerwrapper.make_tags(TAGGER[lang].tag_text(text))
    return TwistaList(tags).filter(lambda t: type(t) == treetaggerwrapper.Tag)


'''
Returns all lemmatized nouns of a text using part-of-speech tagging.
:param text String to analyze for nouns
:param lang Language in ISO-code (e.g. 'en' for English, 'de' for German, passed to POS tagger)
:return list of lemmatized nouns
'''
def nouns(text, lang='de'):
    return pos_tagging(text, lang=lang)\
        .filter(lambda t: t.pos in NOUN_TAGS[lang])\
        .map(lambda t: t.lemma)\
        .filter(lambda n: n not in ['RT', 'replaced-dns'])


'''
Returns all lemmas of a text using part-of-speech tagging.
:param text String to analyze for lemmas
:param lang Language in ISO-code (e.g. 'en' for English, 'de' for German, passed to POS tagger)
:return list of lemmas
'''
def lemmatize(text, lang='de'):
    return pos_tagging(text, lang=lang).map(lambda t: t.lemma)

