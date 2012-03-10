Architecture of the web application
===================================

The web application uses the Django web application framework.

Applications
------------

``common``
   Contains functions that are used in other applications. This includes
   libvirt connections, database locks etc.

``registration``
   This application will contain the registration for new users. Currently it
   only contains the templates for login.

``scenario``
   This is the main application. It stores information about scenarios
   (scenario text, required memory, used base image ...), running scenarios
   (who plays what scenario) and secrets (available and submitted secrets).
   It also contains views for viewing scenarios, submitting secrets etc.

``vm``
   Virtual machines and their images are defined in this application's models.
   It contains code for starting, stopping, resuming virtual machines etc.

``network``
   This application handles the network logic. Currently it only defines a
   pool of free IP/MAC addresses.

``pki``
   Certificate management for the VPN is this application's task. It provides
   a method for creating a certificate for a given CSR and views for receiving
   the certificate.

Management commands
-------------------

``loadscenario``
   Loads an scenario. It takes one argument: The directory of where the
   scenario is stored. See :ref:`registering-scenario`.
   This command is defined in the scenario app.

``vmd``
   This is the virtual machine daemon, it manages all virtual machine requests
   (starting, stopping etc.). It also stops virtual machines for expired
   scenario runs.

``network``
   This management commands can do various network tasks. It can fill the pool
   with random IP/MAC address combinations or generate a configuration file
   for the ISC dhcp server.
