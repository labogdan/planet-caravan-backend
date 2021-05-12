import json
import re
import math
import string
import random


def handleize(s=''):
    """
    Create url-friendly handles
    :param s:
    :return str:
    """
    return re.sub(r'-{2,}', '-', re.sub(r'[^a-z0-9\-_]', '-', s.lower())).strip('-')


def has_value(d=None):
    """
    Determines if a value from a read csv cell has an actual value
    :param d:
    :return:
    """
    return (type(d) is str and d != "" and d != "nan") or not math.isnan(d)


def description_block(text=''):
    letters = string.ascii_lowercase
    key = ''.join(random.choice(letters) for _ in range(5))

    if text is not None:
        text = text.replace("\n", " ").replace('"', '\"')

    return json.dumps({"blocks": [
        {
            "key": key,
            "data": {},
            "text": text,
            "type": "unstyled",
            "depth": 0,
            "entityRanges": [],
            "inlineStyleRanges": []
        }
    ],
        "entityMap": {}
    })
