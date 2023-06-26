# Run "nosetests" on command line to run these.
from namecheap import Api, ApiError, Domain
from privex.helpers import is_true
from nose.tools import *  # pip install nose

api_key = ''  # You create this on Namecheap site
username = ''
ip_address = ''  # Your IP address that you whitelisted on the site

# If you prefer, you can put the above in credentials.py instead
try:
    from credentials import api_key, username, ip_address
except:
    pass


def get_api() -> Api:
    return Api(username, api_key, ip_address, sandbox=True, debug=True)


def random_domain_name():
    import random
    from time import gmtime, strftime
    domain_name = "%s-%s.com" % (strftime("%Y%m%d-%H%M%S", gmtime()), random.randint(0, 10**16))
    return domain_name


def test_domain_taken():
    api = get_api()
    domain_name = "google.com"
    assert_equal(api.domains_available(domain_name), False)


def test_domain_available():
    api = get_api()
    domain_name = random_domain_name()
    assert_equal(api.domains_available(domain_name), True)


def test_register_domain():
    api = get_api()

    # Try registering a random domain. Fails if exception raised.
    domain_name = random_domain_name()
    res = api.domains_create(
        DomainName=domain_name,
        FirstName='Jack',
        LastName='Trotter',
        Address1='Ridiculously Big Mansion, Yellow Brick Road',
        City='Tokushima',
        StateProvince='Tokushima',
        PostalCode='771-0144',
        Country='Japan',
        Phone='+81.123123123',
        EmailAddress='jack.trotter@example.com'
    )
    
    assert_equal(res.domain, domain_name)
    ok_(int(res.domain_id) > 0)
    ok_(int(res.transaction_id) > 0)
    ok_(is_true(res.registered))
    return domain_name


def test_domains_getList():
    api = get_api()
    doms = list(api.domains_getList())
    ok_(len(doms) > 0)
    ok_(isinstance(doms[0], Domain))


@raises(ApiError)
def test_domains_dns_setDefault_on_nonexisting_domain():
    api = get_api()

    domain_name = random_domain_name()

    # This should fail because the domain does not exist
    api.domains_dns_setDefault(domain_name)


def test_domains_dns_setDefault_on_existing_domain():
    api = get_api()
    domain_name = test_register_domain()
    res = api.domains_dns_setDefault(domain_name)
    assert_equal(res['Domain'], domain_name)
    ok_(is_true(res['Updated']))


def test_domains_getContacts():
    # How would I test for this? This needs a known registered
    # domain to get the contact info for, but in sandbox won't
    # have any.
    pass


def test_domains_dns_setHosts():
    api = get_api()
    domain_name = test_register_domain()
    res = api.domains_dns_setHosts(
        domain_name,
        dict(HostName='@', RecordType='URL', Address='http://news.ycombinator.com', MXPref='10', TTL='100')
    )
    assert_equal(res['Domain'], domain_name)
    ok_(is_true(res['IsSuccess']))

#
# I wasn't able to get this to work on any public name servers that I tried
# including the ones used in their own example:
#   dns1.name-servers.com
#   dns2.name-server.com
# Using my own Amazon Route53 name servers the test works fine but I didn't
# want to embed my own servers
# Adjust the name servers below to your own and uncomment the test to run


def test_domains_dns_setCustom():
    api = get_api()
    domain_name = test_register_domain()
    result = api.domains_dns_setCustom(
        domain_name, 'ns1.privex.io', 'ns2.privex.io', 'ns3.privex.io'
    )


def test_domains_dns_getHosts():
    api = get_api()
    domain_name = test_register_domain()
    api.domains_dns_setHosts(
        domain_name,
        dict(HostName='@', RecordType='URL', Address='http://news.ycombinator.com', MXPref='10', TTL='100'),
        dict(HostName='*', RecordType='A', Address='1.2.3.4', MXPref='10', TTL='1800')
    )

    hosts = [dict(d.raw_data) for d in api.domains_dns_getHosts(domain_name)]

    # these might change
    del hosts[0]['HostId']
    del hosts[1]['HostId']

    expected_result = [
        {
            'Name': '*',
            'Address': '1.2.3.4',
            'TTL': '1800',
            'Type': 'A',
            'MXPref': '10',
            'AssociatedAppTitle': '',
            'FriendlyName': '',
            'IsActive': 'true',
            'IsDDNSEnabled': 'false'
        }, {
            'Name': '@',
            'Address': 'http://news.ycombinator.com',
            'TTL': '100',
            'Type': 'URL',
            'MXPref': '10',
            'AssociatedAppTitle': '',
            'FriendlyName': '',
            'IsActive': 'true',
            'IsDDNSEnabled': 'false'
        }
    ]
    assert_equal(hosts, expected_result)


def test_domains_dns_addHost():
    api = get_api()
    domain_name = test_register_domain()
    api.domains_dns_setHosts(
        domain_name,
        dict(HostName='@', RecordType='URL', Address='http://news.ycombinator.com')
    )
    api.domains_dns_addHost(
        domain_name,
        record_type='A', value='1.2.3.4', hostname='test', ttl=100
    )

    hosts = api.domains_dns_getHosts(domain_name)
    
    # h1, h2 = hosts[0], hosts[1]
    
    def _find_host(name, address, rtype, mx_pref, ttl):
        for h in hosts:
            if h.name == name and h.address == address:
                assert_equal(h.name, name)
                assert_equal(h.address, address)
                assert_equal(h.type, rtype)
                assert_equal(int(h.mx_pref), int(mx_pref))
                assert_equal(int(h.ttl), int(ttl))
                return
        assert False

    _find_host('@', 'http://news.ycombinator.com', 'URL', 10, 1800)
    _find_host('test', '1.2.3.4', 'A', 10, 100)


def test_domains_dns_bulkAddHosts():
    api = get_api()
    api.payload_limit = 3
    domain_name = test_register_domain()
    api.domains_dns_setHosts(
        domain_name,
        dict(HostName='@', RecordType='URL', Address='http://news.ycombinator.com')
    )
    for i in range(1, 10):
        api.domains_dns_addHost(
            domain_name,
            hostname=f"test{str(i)}", record_type='A', value='1.2.3.4', ttl='60'
        )

    hosts = api.domains_dns_getHosts(domain_name)

    if len(hosts) == 10:
        return True

    return False


def test_domains_dns_delHost():
    api = get_api()
    domain_name = test_register_domain()
    
    res = api.domains_dns_setHosts(
        domain_name,
        dict(HostName='@', RecordType='URL', Address='http://news.ycombinator.com', TTL='200'),
        dict(HostName='test', RecordType='A', Address='1.2.3.4')
    )
    assert_equal(res['Domain'], domain_name)
    ok_(is_true(res['IsSuccess']))
    
    res = api.domains_dns_delHost(domain_name, record_type='A', value='1.2.3.4', hostname='test')
    assert_equal(res['Domain'], domain_name)
    ok_(is_true(res['IsSuccess']))
    
    hosts = api.domains_dns_getHosts(domain_name)
    
    host = hosts[0]
    
    assert_equal(host.name, '@')
    assert_equal(host.address, 'http://news.ycombinator.com')
    assert_equal(host.ttl, 200)
    assert_equal(host.type, 'URL')
    assert_equal(host.mx_pref, 10)


def test_list_of_dictionaries_to_numbered_payload():
    x = [
        {'foo': 'bar', 'cat': 'purr'},
        {'foo': 'buz'},
        {'cat': 'meow'}
    ]

    result = Api._list_of_dictionaries_to_numbered_payload(x)

    expected_result = {
        'foo1': 'bar',
        'cat1': 'purr',
        'foo2': 'buz',
        'cat3': 'meow'
    }

    assert_equal(result, expected_result)


def test_domains_nameserver():
    api = get_api()
    domain_name = test_register_domain()
    
    nameserver = f'ns1.{domain_name}'
    orig_ip = '1.2.3.4'
    new_ip = '11.22.33.44'
    
    res = api.domains_ns_create(domain_name, nameserver=nameserver, ip=orig_ip)
    
    assert_equal(res['Domain'], domain_name)
    assert_equal(res['Nameserver'], nameserver)
    assert_equal(res['IP'], orig_ip)
    ok_(is_true(res['IsSuccess']))
    
    res = api.domains_ns_update(domain_name, nameserver=nameserver, old_ip=orig_ip, ip=new_ip)
    
    assert_equal(res['Domain'], domain_name)
    assert_equal(res['Nameserver'], nameserver)
    ok_(is_true(res['IsSuccess']))
    
    res = api.domains_ns_getInfo(domain_name, nameserver=nameserver)
    
    assert_equal(res['Domain'], domain_name)
    assert_equal(res['Nameserver'], nameserver)
    assert_equal(res['IP'], new_ip)
    
    res = api.domains_ns_delete(domain_name, nameserver=nameserver)
    
    assert_equal(res['Domain'], domain_name)
    assert_equal(res['Nameserver'], nameserver)
    ok_(is_true(res['IsSuccess']))
