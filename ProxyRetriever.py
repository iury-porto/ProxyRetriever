import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import unidecode
import threading
import queue
from useragent_list import useragent_list as ua_list

user_agents = ['Mozilla/5.0 (X11; CrOS i686 4319.74.0) AppleWebKit/537.36 (KHTML, like Gecko)']

def get_sslproxies(noport=False):
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
        if noport is False:
            proxies.append({
                'https': f'{ip}:{port}'
            })
        else:
            proxies.append({
                'https': f'{ip}'
            })
    return proxies


class ThProxyChecker(threading.Thread):
    """Threaded Proxy Checker"""
    def __init__(self, check_fun, proxy_queue, fast_queue, stop_event, *args, **kwargs):
        threading.Thread.__init__(self)
        self.queue = proxy_queue
        self.out_queue = fast_queue
        self.check_proxy = check_fun
        self.args = args
        self.kwargs = kwargs
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            # get a proxy from queue
            try:
                proxy = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            # do work on that proxy
            out = self.check_proxy(proxy, *self.args, **self.kwargs)

            # if the proxy is fast, add it to the output queue
            if out:
                self.out_queue.put(proxy)

            # all is done
            self.queue.task_done()


def get_ip(proxy, timeout=1):
    with requests.Session() as s:
        req = s.get('https://icanhazip.com', proxies=proxy, timeout=timeout)
        req.raise_for_status()
    my_ip = unidecode.unidecode(req.text).strip()
    return my_ip


def check_proxy_i(proxy, i=0, timeout=1, verbose=True):
    try:
        my_ip = get_ip(proxy, timeout)
        if verbose:
            print(f'#{i}: Proxy {str(proxy["https"])} is fast. My IP = {my_ip}.')
        return True
    except requests.RequestException:  # If error, delete this proxy and find another one
        if verbose:
            print(f'#{i}: Proxy {str(proxy["https"])} is slow.')
        return False


def check_proxy(proxy, timeout=1, verbose=True):
    try:
        my_ip = get_ip(proxy, timeout=timeout)
        if verbose:
            print(f'#: Proxy {str(proxy["https"])} is fast. My IP = {my_ip}.')
        return True
    except requests.RequestException:  # If error, delete this proxy and find another one
        if verbose:
            print(f'#: Proxy {str(proxy["https"])} is slow.')
        return False


class ProxyRetriever:
    def __init__(self, get_proxies_fun=get_sslproxies, check_proxy_fun=check_proxy, th_worker=ThProxyChecker):
        self.get_proxies = get_proxies_fun
        self.proxies = []
        self.fast_proxies = []
        self.th_worker = th_worker
        self.check_proxy = check_proxy_fun

    def __call__(self, nthreads=100, timeout=1, verbose=False, threaded=True, include_useragent=False, noport=False):
        self.proxies = self.get_proxies(noport)
        if threaded is True:
            self.th_update_fast_proxies(nthreads, timeout, verbose)
        else:
            self.update_fast_proxies(timeout,verbose)
        if include_useragent is not False:
            n_fast_proxies = len(self.fast_proxies)
            useragent_list = [ua_list[i%n_fast_proxies] for i in range(n_fast_proxies)]
            return list(zip(self.fast_proxies, useragent_list))
        else:
            return self.fast_proxies

    def refresh_proxies(self):
        self.proxies = self.get_proxies()

    def update_fast_proxies(self, timeout=1, verbose=True):
        fast_proxies = []
        for proxy, i in zip(self.proxies, range(len(self.proxies))):
            if check_proxy_i(proxy, i, timeout=timeout, verbose=verbose):
                fast_proxies.append(proxy)
        self.fast_proxies = fast_proxies

    def th_update_fast_proxies(self, nthreads=100, timeout=1, verbose=True):
        proxy_q = queue.Queue()
        fast_q = queue.Queue()
        # Spawn threads
        thread_list = []
        stop_event = threading.Event()

        for i in range(nthreads):
            t = self.th_worker(self.check_proxy, proxy_q, fast_q, stop_event, timeout=timeout, verbose=verbose)
            # t.setDaemon(True)
            t.start()
            thread_list.append(t)

        # Populate queue with proxies
        for p in self.proxies:
            proxy_q.put(p)

        # Wait on the queues
        proxy_q.join()

        # Kill threads
        stop_event.set()

        # Update the fast list
        self.fast_proxies = list(fast_q.queue)
