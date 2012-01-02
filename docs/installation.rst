Installation
============

Installing Debian squeeze
-------------------------

Create a large partition and choose ``/var/lib/libvirt/`` as mountpoint.
It will be used as storage pool for libvirt.

The first user should be named ``insekta``, as we will refer to this name in
the documentation.

Install Debian with standard system utilities and a ssh server. We don't need
a desktop environment or anything else.

Installing Insekta's dependencies
---------------------------------

Login as root and enable ``squeeze-backports`` by editing
``/etc/apt/sources.lst``. Add::
   
   # Squeeze backports
   deb http://backports.debian.org/debian-backports squeeze-backports main

Save the file and execute ``aptitude update``. Now you can install
``libvirt``, ``qemu-kvm`` etc.::
   
   apitude install -t squeeze-backports libvirt-bin python-libvirt

This should install ``qemu-kvm`` as well because it is a recommendation of the
package ``libvirt-bin``.

Insekta is written in Python and needs some python packages::
   
   aptitude install python-psycopg2 virtualenvwrapper

Additional python packages will be installed inside a virtual environment. We
will create it now::
   
   su insekta
   mkdir ~/.virtualenvs
   mkvirtualenv insekta
   pip install django pygments creoleparser gunicorn sphinx
   exit

Nginx will be our reverse proxy for gunicorn and PostgreSQL our database
server. We need to install both::
   
   aptitude install nginx postgresql

Dependencies are now installed :)

Creating storage pool
---------------------

Insekta will store it's images for the virtual machine inside a libvirt
storage pool. Put the following XML into a file ``default-pool.xml``::
   
   <pool type='dir'>
     <name>default</name>
     <target>
       <path>/var/lib/libvirt/images</path>
     </target>
   </pool>

and call ``virsh`` with the command ``pool-define`` to define the pool and
``pool-start`` to start it::
   
   virsh -c qemu:///system pool-define default-pool.xml
   virsh -c qemu:///system pool-start default

All our images will now be saved to ``/var/lib/libvirt/images``.

Configuring network
-------------------

We assume that 192.168.0.* is your local network with 192.168.0.1 being your
gateway. All domains should be reachable within the network, so everyone
inside your network can learn hacking by attacking Insekta's scenarios.

First we will set up a bridge. Stop your interface ``eth0`` by typing::
   
   ifdown eth0

Open ``/etc/network/interfaces`` in your preferred editor. You will some
definition for ``eth0`` which should look like::
   
   allow-hotplug eth0
   iface eth0 inet dhcp

Remove these lines and insert the following::
   
   auto br0
   iface br0 inet static
       address 192.168.0.42
       netmask 255.255.255.0
       network 192.168.0.1
       broadcast 192.168.0.255
       gateway 192.168.0.1
       bridge_ports eth0
       bridge_stp on
       bridge_nowait 0
       bridge_fd 0

Save this file and bring up ``br0``::
   
   ifup bro0

Add the following lines to ``/etc/sysctl.conf``::
   
   net.bridge.bridge-nf-call-ip6tables = 0
   net.bridge.bridge-nf-call-iptables = 0
   net.bridge.bridge-nf-call-arptables = 0

and reload the configuration::
   
   sysctl -p /etc/sysctl.conf

Installing Insekta
------------------

Clone the git, change into Insekta's virtual environment and create the config
file named ``settings.py``::
   
   git clone gitolite@unicorn.gnubo.de:insekta .
   workon insekta
   cd insekta/insekta
   cp settings.py.example settings.py
   vim settings.py

Execute Djangos ``syndb`` and a few other management commands::
   
   ./manage.py syncdb # Create database structure
   ./manage.py compilemessages # Compile translations
   ./manage.py collectstatic # Collect all static files in _static
   ./manage.py network fill # Inserts available IPs into database

For testing, you can run the development server by calling::
   
   ./manage.py runserver 8000

and point your browser (you shouldn't have one on this system :P) to
`http://localhost:8000/ <http://localhost:8000/>`_.

Stop the development server and copy the init script in the scripts
directory to ``/etc/init.d/insekta``::
   
   cp ../examples/insekta-init-script /etc/init.d/insekta

Copy the nginx site configuration to ``/etc/nginx/sites-available/insekta``,
change it to suit your needs and symlink it into ``sites-enabled``::
   
   cp ../examples/insekta-nginx-config /etc/nginx/sites-available/insekta
   vim /etc/nginx/sites-available/insekta # Change ServerName etc.
   ln -s /etc/nginx/sites-available/insekta /etc/nginx/sites-enabled/

Finally restart nginx::
   
   /etc/init.d/nginx restart


