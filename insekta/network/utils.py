import random

def ip_to_int(ip):
    """Packs an IP into an integer, e.g. '127.0.0.1' into 2130706433"""
    ip_int = 0
    for octet in ip.split('.'):
        ip_int = (ip_int << 8) | int(octet, 10)
    return ip_int

def int_to_ip(ip_int):
    """Converts an integer into an IP, e.g. 2130706433 to '127.0.0.1'"""
    octets = [0] * 4
    for i in xrange(4):
        octets[3 - i] = str(ip_int & 0xff)
        ip_int >>= 8
    return '.'.join(octets)

def get_random_ip(blocks):
    """Get an random IP inside a block or a list of blocks."""
    block = random.choice(blocks) if hasattr(blocks, '__iter__') else blocks
    ip, cidr = block.split('/')
    num_ips = 2**(32 - int(cidr, 10)) - 1
    return int_to_ip(ip_to_int(ip) + random.randint(0, num_ips))

