import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import unidecode
import threading
import queue

def get_sslproxies():
    ua = UserAgent()  # From here we generate a random user agent
    proxies = []  # Will contain proxies ['ip:port']

    s = requests.Session()
    proxies_req = s.get('https://www.sslproxies.org/', headers={'User-Agent': ua.random})
    proxies_req.raise_for_status()

    soup = BeautifulSoup(proxies_req.text, 'html.parser')
    proxies_table = soup.find(id='proxylisttable')

    # Save proxies in the array
    for row in proxies_table.tbody.find_all('tr'):
        ip = row.find_all('td')[0].string
        port = row.find_all('td')[1].string
        proxies.append({
            'http': f'{ip}:{port}'
        })
    return proxies


class ThProxyChecker(threading.Thread):
    """Threaded Proxy Checker"""
    def __init__(self, check_fun, proxy_queue, fast_queue, *args, **kwargs):
        threading.Thread.__init__(self)
        self.queue = proxy_queue
        self.out_queue = fast_queue
        self.check_proxy = check_fun
        self.args = args
        self.kwargs = kwargs

    def run(self):
        while True:
            # get a proxy from queue
            proxy = self.queue.get()

            # do work on that proxy
            out = self.check_proxy(proxy, *self.args, **self.kwargs)

            # if the proxy is fast, add it to the output queue
            if out:
                self.out_queue.put(proxy)

            # all is done
            self.queue.task_done()


class ProxyRetriever:
    def __init__(self, get_proxies_fun=get_sslproxies, th_worker=ThProxyChecker):
        self.get_proxies = get_proxies_fun
        self.proxies = get_proxies_fun()
        self.fast_proxies = []
        self.th_worker = th_worker

    def refresh_proxies(self):
        self.proxies = self.get_proxies()

    @staticmethod
    def get_ip(proxy, timeout=1):
        with requests.Session() as s:
            req = s.get('http://icanhazip.com', proxies=proxy, timeout=timeout)
            req.raise_for_status()
        my_ip = unidecode.unidecode(req.text).strip()
        return my_ip

    def check_proxy_i(self, proxy, i=0, timeout=1, verbose=True):
        try:
            my_ip = self.get_ip(proxy, timeout)
            if verbose:
                print(f'#{i}: Proxy {str(proxy["http"])} is fast. My IP = {my_ip}.')
            return True
        except requests.RequestException:  # If error, delete this proxy and find another one
            if verbose:
                print(f'#{i}: Proxy {str(proxy["http"])} is slow.')
            return False

    def check_proxy(self, proxy, timeout=1, verbose=True):
        try:
            my_ip = self.get_ip(proxy, timeout=timeout)
            if verbose:
                print(f'#: Proxy {str(proxy["http"])} is fast. My IP = {my_ip}.')
            return True
        except requests.RequestException:  # If error, delete this proxy and find another one
            if verbose:
                print(f'#: Proxy {str(proxy["http"])} is slow.')
            return False

    def update_fast_proxies(self, timeout=1, verbose=True):
        fast_proxies = []
        for proxy, i in zip(self.proxies, range(len(self.proxies))):
            if self.check_proxy_i(proxy, i, timeout=timeout, verbose=verbose):
                fast_proxies.append(proxy)
        self.fast_proxies = fast_proxies

    def th_update_fast_proxies(self, nthreads=8, timeout=1, verbose=True):
        proxy_q = queue.Queue()
        fast_q = queue.Queue()
        # Spawn threads
        for i in range(nthreads):
            t = self.th_worker(self.check_proxy, proxy_q, fast_q, timeout=timeout, verbose=verbose)
            t.setDaemon(True)
            t.start()

        # Populate queue with proxies
        i = 0
        for p in self.proxies:
            proxy_q.put(p)

        # Wait on the queues
        proxy_q.join()

        # Update the fast list
        self.fast_proxies = list(fast_q.queue)
