Creating scenarios
==================

A scenario is basically a directory containing an image with the scenario, the
description of the scenario and some metadata. 

Scenario files in detail
------------------------

The directory structure will look like:

* simple-buffer-overflow

  * scenario.qcow2
  * metadata.json
  * description.creole
  * media

    * memory-layout.png
    * http-server.tar.gz

scenario.qcow2
^^^^^^^^^^^^^^

This is an image containing the disk for the virtual machine. It's a normal
disk image for QEMU in qcow2 format. See :doc:`openwrt-images` or
:doc:`debian-images` for creating one.

It is references in the metadata, it's name is just a convention.

metadata.json
^^^^^^^^^^^^^

This file contains some metadata about the scenario. It is valid json and
looks like::

   {
       "image": "scenario.qcow2",
       "name": "simple-buffer-overflow",
       "title": "Exploiting simple buffer overflows",
       "memory": 256,
   }

Currently there are 5 directives:

``image``
   The filename of the scenario image.

``name``
   The name of the scenario. Should only contain alphanumeric characters and
   dashes.

``title``
   The title of the scenario.

``memory``
   The amount of memory in megabytes used by the virtual machine.

description.creole
^^^^^^^^^^^^^^^^^^

This file contains the description for the scenario. It describes what the
hacker needs to do to solve the scenario. Additionally it contains
explanations of what's going on.

The description is written in `creole markup <http://www.wikicreole.org/wiki/Home>`_
with some additional macros e.g. ``enterSecret``, ``requireSecret``, ``ip``
and ``spoiler``.

``enterSecret``
   A form that let the hacker enter some secret he obtained by hacking
   something. It takes a list of secrets that are valid in this form. If
   you don't provide such a list it will take any valid secret. Examples::
      
      <<enterSecret>>Text that is shown above the text field<</enterSecret>>

      <<enterSecret 'first secret' 'second'>>Only 2 secrets!<//enterSecret>>

``requireSecret``
   Content inside the ``requireSecret`` is not shown until the hacker has
   submitted some secrets. It takes a list of secrets and shows it's content
   if *any* of those secrets is submitted. Use nesting to implement ``AND``
   instead of ``OR``. Example::
      
      <requireSecret 'thisOne' 'orThat'>>Congratulation!<</requireSecret>>

      <<requireSecret 'thisOne'>>
      <<requireSecret 'andThat'>>
      This will only be shown if both secrets ("thisOne" and "andThat") are
      submitted by the hacker.
      <</requireSecret>>
      <</requireSecret>>

``ip``
   Will be replaced by the IP of the virtual machine if the scenared has
   started. If not, it will use 127.0.0.1 as dummy. Example::
    
    You can attack the machine at http://<<ip>>/

``spoiler``
   A simple javascript based spoiler tag. It's content won't be shown until
   the hacker clicks on "show". Example::

      <<spoiler>>This is *not* shown!<</spoiler>>

You can also link to other scenarios with creole's link syntax::
   
   If this is to boring, try [[advanced-buffer-overflows|the scenario with canaries]].
   

media
^^^^^

Put any files in this directory and you can reference them in your
``description.creole`` like this::

   Download the [[media:simple-buffer-overflow/http-server.tar.gz|HTTP server source code]].

They will be served via HTTP as static files.


Registering the scenario image
------------------------------

Registering is easy::
   
   ./manage.py loadscenario /path/to/your/scenario

If you want to update the image, just call it again.

.. warning::
   Updating a scenario destroys all existing domains that belong to this
   scenario. However, submitted secrets are not lost.
