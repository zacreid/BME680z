'''
    BME680 Library V1.0
    Copyright (C) 2019  Zac Reid

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

	SkyLabs Mini BME680 Python Library
	  Designed for SkyLabs Mini V1 by Zac Reid
	  For use with busio I2C

'''

import time
import struct

#Constants
BME680Address = 0x77

BME680ChipID = 0x61
BME680RegChipID = 0xD0
BME680RegSoftReset = 0xE0

BME680RegGasControl = 0x71
BME680RegHumidtyControl = 0x72
BME680RegStatus = 0x73
BME680RegMeasControl = 0x74
BME680RegConfig = 0x75
BME680RegMeasStatus = 0x1D
BME680RegPressureData = 0x1F
BME680RegTemperatureData = 0x22
BME680RegHumidtyData = 0x25
BME680GasRun = 0x10

BME680CoEfficientADD1 = 0x89
BME680CoEfficientADD2 = 0xE1
BME680ResWait = 0x5A

BME680GasLookupTableOne = (2147483647.0, 2147483647.0, 2147483647.0, 2147483647.0, 2147483647.0,
                   2126008810.0, 2147483647.0, 2130303777.0, 2147483647.0, 2147483647.0,
                   2143188679.0, 2136746228.0, 2147483647.0, 2126008810.0, 2147483647.0,
                   2147483647.0)

BME680GasLookupTableTwo = (4096000000.0, 2048000000.0, 1024000000.0, 512000000.0, 255744255.0, 127110228.0,
                   64000000.0, 32258064.0, 16016016.0, 8000000.0, 4000000.0, 2000000.0, 1000000.0,
                   500000.0, 250000.0, 125000.0)


BME680SampleRates = {
	0: 0b000,
	1: 0b001,
	2: 0b010,
	4: 0b011,
	8: 0b100,
	16: 0b101
}

BME680FilterCoefficient = {
	0: 0b000,
	1: 0b001,
	3: 0b010,
	7: 0b011,
	15: 0b100,
	31: 0b101,
	63: 0b110,
	127: 0b111
}

pModes = {
	"ULP": 33,
	"LP": 3.3,
	"CM": 1
}

class BME680:
	def __init__(self, i2c, address=BME680Address, seaLvlPress=1013.25, heater=True):
		self.i2c = i2c
		self.address = address
		self.seaLvlPress = seaLvlPress
		
		self.write(BME680RegSoftReset, [0xB6]) #resets bme680
		time.sleep(0.005)

		self.verifyBME680()

		self.grabCalibration()

		if heater:
			self.write(BME680ResWait, [0x73, 0x64, 0x65])

		self.PressureOversample = BME680SampleRates[4]
		self.TempOversample = BME680SampleRates[1]
		self.HumOversample = BME680SampleRates[8]
		self.filter = BME680FilterCoefficient[3]

		self.adcPress = None
		self.adcTemp = None
		self.adcHum = None
		self.adcGas = None
		self.gasRange = None
		self.tFine = None

		self.lastReading = 0

		self.powerMode = pModes["CM"]

		self.setup()



	def read(self, reg, length):
		self.i2c.writeto(self.address, bytes([reg & 0xFF]))
		result = bytearray(length)
		self.i2c.readfrom_into(self.address, result)
		return result

	def write(self, reg, data):
		buff = bytearray(2*len(data))
		for i,var in enumerate(data):
			buff[2*i] = reg + i
			buff[2*i+1] = var
		self.i2c.writeto(self.address, buff)

	def grabByte(self, reg):
		return self.read(reg, 1)[0]

	def grabCalibration(self):
		#grabbing coEfficient data from the bme680
		coEfficient = self.read(BME680CoEfficientADD1, 25)
		coEfficient += self.read(BME680CoEfficientADD2, 16)

		coEfficient = list(struct.unpack('<hbBHhbBhhbbHhhBBBHbbbBbHhbb', bytes(coEfficient[1:39]))) #conversion from binary
		coEfficient = [float(x) for x in coEfficient]

		#sort
		self.BME680TempCalibration = [coEfficient[x] for x in [23, 0, 1]]
		self.BME680PressCalibration = [coEfficient[x] for x in [3, 4, 5, 7, 8, 10, 9, 12, 13, 14]]
		self.BME680HumCalibration = [coEfficient[x] for x in [17, 16, 18, 19, 20, 21, 22]]
		self.BME680GasCalibration = [coEfficient[x] for x in [25, 24, 26]]

		#flip flip
		self.BME680HumCalibration[1] *= 16
		self.BME680HumCalibration[1] += self.BME680HumCalibration[0] % 16
		self.BME680HumCalibration[0] /= 16

		self.BME680HeatRange = (self.grabByte(0x02) & 0x30) / 16
		self.BME680HeatValue = self.grabByte(0x00)
		self.SWErr = (self.grabByte(0x04) & 0xF0) / 16

	def verifyBME680(self):
		if self.grabByte(BME680RegChipID) != BME680ChipID:
			raise RuntimeError("BME680 not connected please try again!")

	def setup(self):

		#setup measurment oversample
		self.write(BME680RegMeasControl, [(self.TempOversample << 5) | (self.PressureOversample << 2)])
		self.write(BME680RegHumidtyControl, [self.HumOversample])
		self.write(BME680RegGasControl, [BME680GasRun])

		self.write(BME680RegConfig, [self.filter << 2]) #setting filter

		mode = self.grabByte(BME680RegMeasControl)
		mode = (mode & 0xFC) | 0x00
		self.write(BME680RegMeasControl, [mode])

	def performReading(self):
		mode = self.grabByte(BME680RegMeasControl)
		mode = (mode & 0xFC) | 0x01
		self.write(BME680RegMeasControl, [mode])

	def getReading(self):
		for go in range(100):
			tmp = self.read(BME680RegMeasStatus, 1)
			if (tmp[0] == 0x80):
				break
			time.sleep(0.001)
		self.lastReading = time.monotonic()
		data = self.read(BME680RegMeasStatus, 15)

		self.adcPress = (data[2] << 12) | (data[3] << 4) | (data[4] >> 4)
		self.adcTemp = (data[5] << 12) | (data[6] << 4) | (data[7] >> 4)
		self.adcHum = (data[8] << 8) | data[9]

		self.adcGas = ((data[13] << 2) | (data[14] >> 6))

		self.gasRange = data[14] & 0x0F

		var1 = (self.adcTemp / 8) - (self.BME680TempCalibration[0] * 2)
		var2 = (var1 * self.BME680TempCalibration[1]) / 2048
		var3 = ((var1 / 2) * (var1 / 2)) / 4096
		var3 = (var3 * self.BME680TempCalibration[2] * 16) / 16384
		self.tFine = int(var2 + var3)
		self.lastReading = time.monotonic()


	def oneShot(self):
		if time.monotonic() - self.lastReading < self.powerMode:
			return
		self.performReading()
		self.getReading()
		self.lastReading = time.monotonic()

	@property
	def temperature(self):
		self.oneShot()
		temp = (((self.tFine *5) +128) /256)
		self.temp = temp / 100
		return self.temp

	@property
	def pressure(self):
		self.oneShot()
		var1 = (self.tFine / 2) - 64000
		var2 = ((var1 / 4) * (var1 / 4)) / 2048
		var2 = (var2 * self.BME680PressCalibration[5]) / 4
		var2 = var2 + (var1 * self.BME680PressCalibration[4] * 2)
		var2 = (var2 / 4) + (self.BME680PressCalibration[3] * 65536)
		var1 = (((((var1 / 4) * (var1 / 4)) / 8192) *
				 (self.BME680PressCalibration[2] * 32) / 8) +
				((self.BME680PressCalibration[1] * var1) / 2))
		var1 = var1 / 262144
		var1 = ((32768 + var1) * self.BME680PressCalibration[0]) / 32768
		pres = 1048576 - self.adcPress
		pres = (pres - (var2 / 4096)) * 3125
		pres = (pres / var1) * 2
		var1 = (self.BME680PressCalibration[8] * (((pres / 8) * (pres / 8)) / 8192)) / 4096
		var2 = ((pres / 4) * self.BME680PressCalibration[7]) / 8192
		var3 = (((pres / 256) ** 3) * self.BME680PressCalibration[9]) / 131072
		pres += ((var1 + var2 + var3 + (self.BME680PressCalibration[6] * 128)) / 16)
		self.pres = pres /100
		return self.pres

	@property
	def humidity(self):
		self.oneShot()
		temp = ((self.tFine * 5) + 128) / 256
		var1 = ((self.adcHum - (self.BME680HumCalibration[0] * 16)) -
				((temp * self.BME680HumCalibration[2]) / 200))
		var2 = (self.BME680HumCalibration[1] *
				(((temp * self.BME680HumCalibration[3]) / 100) +
				 (((temp * ((temp * self.BME680HumCalibration[4]) / 100)) /
				   64) / 100) + 16384)) / 1024
		var3 = var1 * var2
		var4 = self.BME680HumCalibration[5] * 128
		var4 = (var4 + ((temp * self.BME680HumCalibration[6]) / 100)) / 16
		var5 = ((var3 / 16384) * (var3 / 16384)) / 1024
		var6 = (var4 * var5) / 2
		hum = (((var3 + var6) / 1024) * 1000) / 4096
		hum /= 1000
		self.hum = hum

		if self.hum > 100:
			self.hum = 100
		if self.hum < 0:
			self.hum = 0
		return self.hum

	@property
	def gas(self):
		self.oneShot()
		var1 = ((1340 + (5 * self.SWErr)) * (BME680GasLookupTableOne[self.gasRange])) / 65536
		var2 = ((self.adcGas * 32768) - 16777216) + var1
		var3 = (BME680GasLookupTableTwo[self.gasRange] * var1) / 512
		gas = (var3 + (var2 / 2)) / var2
		self.g = int(gas)
		return self.g
