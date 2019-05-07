import logging

from pyyasdi.objects import Plant

logging.basicConfig(level=logging.DEBUG)

sma = Plant(debug=1, max_devices=9)

data = sma.data_all(parameter_channel=False)

print(data)
