Creating images based on Debian
===============================

Creating a raw image and installing Debian
------------------------------------------

The following command creates a raw image named "debian-base.img" with a size
of 10 GiB::

   kvm-img -f raw debian-base.img 10G

Now you can download a Debian netinstall image from the `Debian website
<http://debian.org/>`_ and boot it::

   kvm debian-base.img -net nic -net user -cdrom debian-6.0.3-amd64-netinst.iso

After booting you can install Debian. It is recommended to create a swap
partition of 100 MB first and use the remaining space for ``/``::

   Disk /dev/loop0: 10.7 GB, 10737418240 bytes
   255 heads, 63 sectors/track, 1305 cylinders, total 20971520 sectors
   Units = sectors of 1 * 512 = 512 bytes
   Sector size (logical/physical): 512 bytes / 512 bytes
   I/O size (minimum/optimal): 512 bytes / 512 bytes
   Disk identifier: 0x000e2f02

         Device Boot      Start         End      Blocks   Id  System
   /dev/sda1               2048      194559       96256   82  Linux swap / Solaris
   /dev/sda2                 20969471    10387456   83  Linux

Using this partition layout you can easily shrink the image after installing
the scenario.

Mounting the image for scenario installation
--------------------------------------------

It is recommended to create a backup of your image before modifying it. Using
a backup you can create multiple scenarios without installing Debian several
times :)

To mount the root partition of the image you need to setup a loop device. This
can be done using ``losetup``. First you have to find out the start offset of
the root partition. This can be done with ``fdisk``::

   losetup -fv debian-base.img # Reports "Loop device is /dev/loop0"
   fdisk /dev/loop0

Now use ``p`` to print the partition table. It will look like above. To get the
offset you multiply the start block by the physical sector size (512 bytes).
In the example above: 194560 * 512 = 99614720. This offset can be given to
losetup to create a loop device with the root partition.

To create the loop device with loop partition, just call ``losetup`` with the
``-o`` parameter and the offset::

    losetup -fv debian-base.img -o 99614720 # Reports "Loop device is /dev/loop1"

Create a mount point for the root partition and mount it::

   mkdir /mnt/scenario
   mount /dev/loop1 /mnt/scenario

Now you can ``chroot`` into the system::

   mount --bind /dev /mnt/scenario/dev
   mount --bind /sys /mnt/scenario/sys
   mount --bind /proc /mnt/scenario/proc
   chroot /mnt/scenario /bin/bash

Congratulation, you are now ready to install your scenario! Just do whatever
is necessary: Installing packages, copying files etc.

As the last step you should edit ``/etc/udev/rules.d/70-persistent-net.rules``
and remove all entries. udev uses this file to get the network interface name
for the current mac address, which will change when starting a scenario. If
you remove all entries, the interface name will be ``eth0``.

After installation of your scenario you can quit the ``chroot`` by pressing
``Ctrl+D`` and unmount the partition::

   umount /mnt/scenario/dev
   umount /mnt/scenario/sys
   umount /mnt/scenario/proc
   umount /mnt/scenario

If you don't won't to shrink the image, you can destroy the loop devices::
   
   loop -d /dev/loop0
   loop -d /dev/loop1

Shrinking the image
-------------------

To shrink the image, you have to shrink the root partition first. Get the
current space usage by mounting the partition again and run ``df``::
   
   mount /dev/loop1 /mnt/scenario
   df

You will see an output like this::

   Filesystem            Size  Used Avail Use% Mounted on
   [...]
   /dev/loop0            9.8G  524M  8.8G   6% /mnt/scenario

After unmounting you can resize the filesystem on the partition. You can use
``resize2fs`` to shrink the filesystem after checking it with ``e2fsk``. Just
add a about 100 MB to the used space to get the new size::
   
   umount /dev/scenario
   e2fsk -f /dev/loop1
   resize2fs /dev/loop1 630M

Now we need to change the partition table and resize the root partition
itself. Call fdisk to delete the root partition and create a new one with the
filesystem's size::

   fdisk /dev/loop0

Enter ``d`` to delete partition number 2 and ``n`` to create a new primary
partition. The partition number should be 2 and the first sector should be
the last sector of partition 1 plus one. Last sector should be the new size
e.g. ``+630M``. Before saving the changes by entering ``w`` write down
the last partition's last sector, you will need it to reduce the image
file's size.

You don't need the loop file systems any more, just destroy it::

   losetup -d /dev/loop0
   losetop -d /dev/loop1

There is only one thing left: Reducing the size of the image file itself.
This can be done by using ``dd`` with the ``count`` parameter. This should be
set to last partition's last block plus 2 [#f1]_. ``bs`` parameter should be
set to the physical block size::

   dd if=debian-base.img of=scenario.img bs=512 count=1484801
   kvm-img convert -O qcow2 scenario.img scenario.qcow2
   rm scenario.img

.. rubric:: Footnotes

.. [#f1] According to `some blog article <http://www.blog.turmair.de/2010/11/how-to-shrink-raw-qemu-kvm-images/>`_ but without any explanation :(
