"""
Basic colors for terminals
"""

def printline(color='', message=''):
    print(f'{color}{message}\033[39m')


def error(message=''):
    printline('\033[31m', message)


def info(message=''):
    printline('\033[36m',message)


def warning(message=''):
    printline('\033[33m', message)


def comment(message=''):
    printline('\033[32m', message)