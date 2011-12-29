import libvirt

from django.conf import settings

class VirtError(Exception):
    pass

class ConnectionHandler(object):
    def __init__(self, libvirt_nodes):
        self.libvirt_nodes = libvirt_nodes
        self._connections = {}

    def __getitem__(self, key):
        if key not in self._connections:
            try:
                connection_url = self.libvirt_nodes[key]
            except KeyError:
                raise VirtError('No such node')
            connection = libvirt.open(connection_url)
            self._connections[key] = connection

        return self._connections[key]

    def __iter__(self):
        return iter(self.libvirt_nodes)

    def __del__(self):
        for conn in self._connections.values():
            conn.close()

connections = ConnectionHandler(settings.LIBVIRT_NODES)
