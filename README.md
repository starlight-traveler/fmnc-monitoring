## Airodump Packet Side Project

### University of Notre Dame - Wireless Institute

This is minimal documentation on how to setup the packet monitoring dameon, gpsd dameon, in order to log data via OpenWRT Router One.

The following hardware is needed

> OpenWRT One Router

> Localhost/Closed Static Network (Or Manual Interface Assignment)

> NEMA Output GPS

To start, follow the OpenWRT One Router setup interface and connect to it either over multicast or the dedicated IP address, in my setup I set the local manual IP address:

https://openwrt.org/toh/openwrt/one

The device will manually assign itself to 192.168.1.1, just make sure your local computer interface is aware of that/assign itself that IP address.

Stock OpenWRT router may come in a **release** candidate state. Which means at this time, they must be updated because the *opkg* install system will not see the 24.10.0 releases and instead see the 24.10.0-r* releases which will cause a failure to install packages needed to run

**This was a big source of headache for an entire week so update please!**

Download the "SYSUPGRADE" from the following website, you will have to input the OpenWRT One router on the top and then scroll down.

https://firmware-selector.openwrt.org

Once that file is installed, go to the UI at 192.168.1.1 and go to the settings tab, while it may be a bit different, you need to look for the upgrade OS button and simply upload the SYSUPGRADE from your computer onto that tab

https://openwrt.org/docs/guide-user/installation/generic.sysupgrade

Once it restarts you are good to go!

I also suggest to connect it to a publicly available WiFi network as a client, just nice to make sure the radios are working properly.

## SSH & Setting Up Monitor Mode

In the LuCi (Web UI) add your ssh keys, it will make life a lot easier. Then simply ssh as root to the 192.168.1.1 interface, enter the password if you need to.

Once in we need to install a few things, so run the following commands:

> opkg update

> opkg install aircrack-ng cmake gcc g++ make python3-dev python3-pip

Anytime you install anything, make sure to run *opkg update* first or else it may throw an error that looks like you do not have a network connection.

Secondly we need to add monitor mode interfaces on both ports, so lets do that.

There are two physical radios on the OpenWRT One, so we need to create two new interfaces, here is how I chose to do it.

See here for the physical interfaces:

> iw dev

> iw list

2.4 GHz Radio

> iw phy phy0 interface add mon0 type monitor

> ifconfig mon0 up

5.0 GHz Radio

> iw phy phy1 interface add mon5 type monitor

> ifconfig mon5 up

Once those monitoring interfaces are setup, airdump can be ready to go, the commands to run that are as follows, if we are not using the script:

2.4 GHz Radio

> airodump-ng -w capture_file --output-format pcap,csv,netxml mon0

5 GHz Radio

> airodump-ng -w capture_file --output-format pcap,csv,netxml mon5

**These can be run at the same time, just create a new terminal instance**

These can be done for the other physical interfaces on the ETH ports, but will not be getting into that here.

## GPS Dameon

In order to get GPS working you have to connect it via USB TTL on the one USB A port. It has to transmit NEMA sentences. This will pinpoint the GPS coordinates of the access point inline with where it is.

So in order to do that install

> opkg update

> opkg install gpsd

Once gpsd is installed we will need to also also install *screen*

> opkg update

> opkg install screen

Once screen is installed then we can configure the GPS dameon such that the process can see and use it properly, these are the configurations:

> $ gpsd /dev/ttyS1 /*Using default settings*/

> OR

> $ gpsd /dev/ttyS1 -n /*gpsd will read NMEA data from device even if no client >is running*/

> OR

> $ gpsd /dev/ttyS1 -n -N -D 3 /*gpsd will read NMEA data from device  even if >no client is running, don't send gpsd into background, debug setting 3 >>>(verbose)*/

Also install the clients to watch it work:

> opkg update

> opkg install gpsd-clients

Such that start the client in terminal after finding the port in /dev/tty* in order to see it working, detach it when necessary

### Program

The python program instruments the airodump process and produces output based on the configuration files. At this time it requires no additional pip installs, even though we installed pip earlier.

The python program has the following configuration:

```
{

    "interface": "mon0",

    "use_band": true,

    "band": "false",

    "channel_hop_time": 2,

    "duration": "infinite",

    "output_prefix": "test",

    "min_free_space_mb": 50,

    "use_gpsd": false,

    "output_formats": ["netxml", "pcap", "csv"],

    "space_check_interval": 30

}
```

The interface is the physical interface attached to iw, so if you want to use the 5 GHz radio change it to mon5

If needed, the use_band option is if you want to limit the chancel scan, setting band to false will simply ignore this.

Channel hop time is how long it waits on each channel in seconds.

Duration can set to how long you want the program to run.

Prefix for the output, will be followed by a date and time stamp in the folder

Minimum free space the program should be operating with in MB.

Whether or not you want to enable gpsd and if that is working

The output formats. There are a great many more output formats supported, but these are the ones most pertienent. There is a utility python script to convert the netxml to a kml file that we can use in Google Earth to process the data.

PCAP files are fully usable in Wireshark, utility files can screen for Block ACKs and other data.

CSV is s generic list of SSIDs and other data that is generally useful, will output as a default.

How often we are querying the disk to see how much space is left.

### Conclusion

That should be it! The program should be set for monitor mode, if there are nay questions please feel free to reach out.
