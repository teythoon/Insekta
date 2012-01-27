Creating images based on OpenWRT
================================

This document is written for debian like operating systems, if you use
any other system you will have to install the equivalent packages for
your distribution.

Note that building OpenWRT requires at least 5 gigabytes of hard disk
space and about two hours on a modest machine.

Please run all these commands as a non privileged user.

Initial setup
-------------

We need to checkout OpenWRT and install a few build dependencies.

::

   % sudo aptitude install build-essential zlib1g-dev libncurses-dev \
                           git subversion gawk unzip flex gcc-multilib
   % git clone git://nbd.name/openwrt.git
   % cd openwrt
   % echo src-git packages git://nbd.name/packages.git > feeds.conf
   % ./scripts/feeds update
   % ./scripts/feeds install -a

The most likely reason for any issues you might encounter at this
point are missing build dependencies. Install any missing packages and
update this document.

Updating OpenWRT
----------------

To update your checkout, just run

::

   % cd openwrt
   % git pull
   % ./scripts/feeds update

Template creation
-----------------

Let's do some basic configuration of the image, stuff like target
system, network configuration and package selection.

::

   % ./scripts/env new template
   % make menuconfig
   [curses based configuration menu appears]

   Target System  ---> x86
   Subtarget  ---> KVM Guest
   Target Images  --->
      [*] ext4
      [ ] jffs2
      [ ] squashfs
      (0) Seconds to wait before booting the default entry
   Global build settings  --->
      [*] Compile certain packages parallelized
      (3) Number of package submake jobs (2-512)
      [*] Parallelize the default package build rule (May break build)
      [*] Parallelize the toolchain build (May break build)
   [*] Image configuration  --->
      (dhcp) LAN Protocol
      [*] Preinit configuration options  --->
         (0) Failsafe wait timeout
         [*] Suppress network message indicating failsafe
   Base system  --->
      < > dnsmasq
      < > dropbear
   Network  --->
      SSH  --->
         <*> openssh-server
         <*> openssh-sftp-server
      < > ppp

Personalizing the template
--------------------------

::

   % mkdir -p files/{etc/,root/.}ssh
   % for type in rsa dsa; do {
        /usr/bin/ssh-keygen -N '' -t "${type}" -f "files/etc/ssh/ssh_host_${type}_key"
     }; done
   % cat ~/.ssh/id_rsa.pub >> files/root/.ssh/authorized_keys

Saving the changes
------------------

::

   % ./scripts/env save

Creating an image
-----------------

The ``./scripts/env`` script stores the image configuration and files
below ``./files`` in a git repository. Let's make sure that we're in
the template environment and create a new one.

::

   % ./scripts/env switch template
   % ./scripts/env new unix_security_0x0002
   Do you want to clone the current environment? (y/N): y<enter>

You can now use ``make menuconfig`` to install any packages needed for
your scenario and put files into ``./files``.

::

   % make
   % make[1] world
   [...]
   % wc --bytes bin/x86/openwrt-x86-kvm_guest-combined-ext4.img.gz
   4030079 bin/x86/openwrt-x86-kvm_guest-combined-ext4.img.gz
