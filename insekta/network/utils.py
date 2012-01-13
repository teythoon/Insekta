def ip_to_int(ip):
    """Pack an IP into an integer, e.g. '127.0.0.1' into 2130706433"""
    ip_int = 0
    for octet in ip.split('.'):
        ip_int = (ip_int << 8) | int(octet, 10)
    return ip_int

def int_to_ip(ip_int):
    """Convert an integer into an IP, e.g. 2130706433 to '127.0.0.1'"""
    octets = [0] * 4
    for i in xrange(4):
        octets[3 - i] = str(ip_int & 0xff)
        ip_int >>= 8
    return '.'.join(octets)

def cidr_to_netmask(cidr):
    """Convert a cidr to a netmask, e.g. /28 (as int) to 255.255.255.240."""
    return 0xffffffff ^ (1 << 32 - cidr) - 1

def iterate_ips(block):
    """Iterate over all IPs in an IP block."""
    ip, cidr = block.split('/')
    num_ips = 1 << (32 - int(cidr, 10))
    min_ip = ip_to_int(ip)
    for i in xrange(num_ips):
        yield min_ip + i

def iterate_nets(block, net_size):
    """Iterate over all nets in an IP blocks."""
    next_net_offset = 1 << (32 - net_size)
    ip, cidr = block.split('/')
    max_net_ip = ip_to_int(ip) + (1 << (32 - int(cidr, 10)))
    net_ip_int = ip_to_int(ip)
    while net_ip_int < max_net_ip:
        yield net_ip_int
        net_ip_int += next_net_offset

