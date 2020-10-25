import re


def prepare_spider_name(name):
    name = name.replace('.', '_')
    name = name.replace('-', '_')

    return re.sub(r'(^%d+)', '_', name)
