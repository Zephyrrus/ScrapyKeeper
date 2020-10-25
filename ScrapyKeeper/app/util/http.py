import logging
import requests
from ScrapyKeeper import config


def request_get(url, retry_times=5, **kwargs):
    for i in range(retry_times):
        try:
            res = requests.get(url, params=None, **kwargs)
        except Exception as e:
            logging.warning('request error retry %s' % url)
            continue
        return res


def request_post(url, data, retry_times=5, **kwargs):
    '''
    :param url:
    :param retry_times:
    :return: response obj
    '''
    for i in range(retry_times):
        try:
            res = requests.post(url, data, json=None, **kwargs)
        except Exception as e:
            logging.warning('request error retry %s' % url)
            continue
        return res


def request(request_type, url, data=None, retry_times=5, return_type="text", **kwargs):
    '''

    :param request_type: get/post
    :param url:
    :param data:
    :param retry_times:
    :param return_type: text/json
    :return:
    '''

    kwargs.setdefault('timeout', config.DEFAULT_TIMEOUT)

    if request_type == 'get':
        res = request_get(url, retry_times, **kwargs)
    if request_type == 'post':
        res = request_post(url, data, retry_times, **kwargs)
    if not res: return res
    if return_type == 'text': return res.text
    if return_type == 'json':
        try:
            res = res.json()
            return res
        except Exception as e:
            logging.warning('parse json error %s' % str(e))
            return None
