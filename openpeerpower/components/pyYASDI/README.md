pyYASDI - yasdi for unix with some bugfixes
=========


## Installation


Get yasdi source code from http://www.sma.de/en/products/monitoring-control/yasdi.html.

```
# on raspberry pi
mkdir yasdi
cd yasdi
wget http://www.sma.de/yasdi-source-code.html
unzip yasdi-source-code.html
sudo apt-get install -y cmake
cd projects/generic-cmake
mkdir build-gcc
cd build-gcc
cmake ..
make
sudo make install  

sudo ldconfig

# logout and login to update
# paths for libraries, otherwise set
export LD_LIBRARY_PATH=/usr/local/lib/

# clone this repo
cd ~
git clone git@github.com:plieningerweb/pyYASDI.git
cd pyYASDI

# this assumes that you have an RS485 converter on /dev/ttyUSB0
# connected to your inverters
# otherwise change yasdi.ini
python read_all.py
```

## Links

* https://github.com/Donderda/SMysqLogger/tree/master/yasdi
