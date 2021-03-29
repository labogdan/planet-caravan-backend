import re
import math

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
