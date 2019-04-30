# BME680z
Python Library for Bosch BME680 Sensor via I2C

<code>
  import board\n
  import busio\n
  import bme680z\n
  i2c = busio.I2C(board.SCL, board.SDA)\n
  \n
  bme = bme680z.BME680(i2c)\n
  \n
  bme.temperature\n
  bme.humidty\n
  bme.pressure\n
  bme.gas\n
</code>
