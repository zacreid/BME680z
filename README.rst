# BME680z
Python Library for Bosch BME680 Sensor via I2C

.. code:: python

    import bme680z
    import board
    import busio
    
    i2c = busio.I2C(board.SCL, board.SDA)
    
    bme = bme680z.BME680(i2c)
    
    bme.temperature
    bme.humidity
    bme.pressure
    bme.gas
