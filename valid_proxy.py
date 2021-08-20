def is_bad_proxy(proxy):
    try:
        import httplib2
        import socks
        import requests

        timeout = 2

        socks.set_default_proxy(proxy[0], proxy[1], proxy[2])
        print(socks.get_default_proxy())
        socks.wrapmodule(httplib2)
        proxy_client = httplib2.Http()

        resp = requests.get(url='http://google.com', verify=False, timeout=timeout)
        if resp.status_code != 200:
            proxy_client.close()
            socks.setdefaultproxy(None)
            return True

        proxy_client.close()
        socks.setdefaultproxy(None)

        return False
    except Exception as e:
        print(e)
        return True
