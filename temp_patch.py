import re
NUM = r'(?:\d+(?:\.\d+)?(?:e[+\-]?\d+)?)'
text = ('A stepped steel shaft ABCD has segment AB 0.30 m long with 50 mm diameter, '
        'segment BC 0.20 m long with 40 mm diameter, and segment CD 0.15 m long with 35 mm diameter.')
sentence_pattern = re.compile(r'[^\.;\n]+')
diam_pattern = re.compile(r'(?P<diam>' + NUM + r')\s*(?P<unit>mm|cm|m|in)\s*(?:diameter|dia)', re.I)
length_patterns = [
    re.compile(r'(?P<len>' + NUM + r')\s*(?P<unit>mm|cm|m|in)\s*(?:long|length|span)', re.I),
    re.compile(r'(?:length|span)\s*(?:of\s*)?(?P<len>' + NUM + r')\s*(?P<unit>mm|cm|m|in)', re.I)
]
for sentence_match in sentence_pattern.finditer(text):
    sentence = sentence_match.group(0)
    diam_matches = list(diam_pattern.finditer(sentence))
    length_candidates = {}
    for pat in length_patterns:
        for lm in pat.finditer(sentence):
            length_candidates.setdefault(lm.start(), lm)
    length_matches = list(length_candidates.values())
    print('Sentence:', sentence)
    print('Diam matches:', [m.groupdict() for m in diam_matches])
    print('Length matches:', [m.groupdict() for m in length_matches])
