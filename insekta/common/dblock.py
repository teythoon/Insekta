from django.db import connection

class dblock(object):
    def __init__(self, lock_type, obj_pk=0):
        self.lock_type = lock_type
        self.obj_pk = obj_pk

    def acquire(self):
        if connection.vendor != 'postgresql':
            # PostgreSQL is the preferred deployment setup, for
            # local testing with sqlite we need no locking
            return
        c = connection.cusor()
        c.execute('SELECT pg_advisory_lock({0:d}, {1:d});'.format(
                self.lock_type, self.obj_pk))
    
    def release(self):
        if connection.vendor != 'postgresql':
            return
        c = connection.cursor()
        c.execute('SELECT pg_advisory_unlock({0:d}, {1:d});'.format(
                self.lock_type, self.obj_pk))
    
    def __enter__(self):
        self.acquire()
    
    def __exit__(self, exc_type, exc_value, tb):
        self.release()
        return exc_type is None

