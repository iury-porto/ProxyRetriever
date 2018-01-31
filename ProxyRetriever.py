import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import unidecode


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


class ProxyRetriever:
    def __init__(self, get_proxies_fun):
        self.get_proxies = get_proxies_fun
        self.proxies = get_proxies_fun()
        self.fast_proxies = []

    def refresh_proxies(self):
        self.proxies = self.get_proxies()

    @staticmethod
    def get_ip(proxy, timeout=1):
        with requests.Session() as s:
            req = s.get('http://icanhazip.com', proxies=proxy, timeout=timeout)
            req.raise_for_status()
        my_ip = unidecode.unidecode(req.text).strip()
        return my_ip

    def check_proxy(self, proxy, i=0, timeout=1, verbose=True):
        try:
            my_ip = self.get_ip(proxy, timeout)
            if verbose:
                print(f'#{i}: Proxy {str(proxy["http"])} is fast. My IP = {my_ip}.')
            return True
        except requests.RequestException:  # If error, delete this proxy and find another one
            if verbose:
                print(f'#{i}: Proxy {str(proxy["http"])} is slow.')
            return False

    def update_fast_proxies(self, timeout=1, verbose=True):
        fast_proxies = []
        for proxy, i in zip(self.proxies, range(len(self.proxies))):
            if self.check_proxy(proxy, i, timeout, verbose):
                fast_proxies.append(proxy)
        self.fast_proxies = fast_proxies
