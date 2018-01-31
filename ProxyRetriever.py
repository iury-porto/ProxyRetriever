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

    def update_fast_proxies(self, timeout=1, verbose=True):
        fast_proxies = []
        for proxy, i in zip(self.proxies, range(len(self.proxies))):
            try:
                with requests.Session() as s:
                    req = s.get('http://icanhazip.com', proxies=proxy, timeout=timeout)
                    req.raise_for_status()
                my_ip = unidecode.unidecode(req.text).strip()
                fast_proxies.append(proxy)
                if verbose:
                    print(f'#{i}: Proxy {str(proxy["http"])} is fast. My IP = {my_ip}.')

            except:  # If error, delete this proxy and find another one
                del self.proxies[i]
                if verbose:
                    print(f'#{i}: Proxy {str(proxy["http"])} is slow.')
        self.fast_proxies = fast_proxies
