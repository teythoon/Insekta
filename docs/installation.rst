Installation
============

Installing Debian squeeze
-------------------------

Create a large logical volume group. It will be used as storage pool for
libvirt.

.. warning::
   Do not install system partitions into this volume group! Use own partitions
   or own volume group instead.

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
   pip install django pygments creoleparser jinja2 gunicorn sphinx
   exit

Nginx will be our reverse proxy for gunicorn, we need to install it::
   
   aptitude install nginx

Dependencies are now installed :)


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


Adding a storage pool
---------------------

libvirt uses storage pools to store the images for its domains. We will use
our logical volume group as storage pool. Find out it's name::
   
  vgdisplay
  --- Volume Group ---
  VG Name               insekta
  [...]

Create a pool xml definition ``insekta-pool.xml``::
   
   <pool type="logical">
       <name>insekta</name>
       <target>
           <path>/dev/insekta</path>
       </target>
   </pool>

Now you can define the storage pool and start it using this xml file::
   
   virsh -c qemu:///system pool-define insekta-pool.xml
   virsh -c qemu:///system pool-autostart insekta
   virsh -c qemu:///system pool-start insekta


