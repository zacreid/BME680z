# BME680z
Python Library for Bosch BME680 Sensor via I2C

.. code:: python
  import board
  import busio
  import bme680z
  i2c = busio.I2C(board.SCL, board.SDA)
  
  bme = bme680z.BME680(i2c)
  
  bme.temperature
  bme.humidty
  bme.pressure
  bme.gas

