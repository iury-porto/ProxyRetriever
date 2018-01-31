from ProxyRetriever import ProxyRetriever, get_sslproxies

PR = ProxyRetriever(get_sslproxies)
PR.update_fast_proxies(timeout=0.5)