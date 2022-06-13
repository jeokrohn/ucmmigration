from ucmexport import Proxy

if __name__ == '__main__':
    proxy = Proxy('sample.tar')
    phones = proxy.phones.list
    print(f'{len(phones)} phones in TAR')
    phones_w_multiple_lines = [phone for phone in phones
                               if len(phone.lines)> 1]
    print(f'{len(phones_w_multiple_lines)} phones with multiple lines')