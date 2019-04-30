# BME680z
Python Library for Bosch BME680 Sensor via I2C

.. code:: python

    from busio import I2C
    from board import SDA, SCL

    i2c = I2C(SCL, SDA)
