from ProxyRetriever import ProxyRetriever, get_sslproxies
import time
import threading

# Non threaded implementation
# start = time.time()
# PR = ProxyRetriever()
# PR.update_fast_proxies(timeout=0.5)
# print(f'Time elapsed: {time.time() - start} s')

#Threaded implementation
# start = time.time()
# PR = ProxyRetriever()
# PR.th_update_fast_proxies(timeout=5, nthreads=100, verbose=True)
# print(f'Time elapsed: {time.time() - start} s')
#print(PR.fast_proxies)
#print(len(PR.fast_proxies))

# for t in tlist:
#     print(f'{t.name}: {t.isactive}')
# print('~~~~~~~~~~~~~')
# for t in list(threading.enumerate()):
#     print(t.isAlive())

# a = ProxyRetriever()
# a.th_update_fast_proxies()

b = ProxyRetriever()
lista, listb = b(verbose=True, include_useragent=True)
for p, ua in zip(lista, listb):
    print(f'Proxy: {p}, UserAgent: {ua}')