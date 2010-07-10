#! /usr/bin/env python2.6
'''
p_dac.py:  Builtin DAC/ADC DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class DAC(Processor):
	def __init__(self, *initargs):
		Processor.__init__(self, 1, 0)

		if len(initargs):
			channel = initargs[0]
		else:
			channel = 0

		self.dsp_inputs = [0]
		self.dsp_init("dac~")
		self.dsp_setparam("channel", channel)
		

	def trigger(self):
		try:
			channel = int(self.inlets[0])
			self.dsp_setparam("channel", channel)
		except:
			print "Can't convert %s to a channel number" % self.inlet[0]
				
class ADC(Processor):
	def __init__(self, *initargs):
		Processor.__init__(self, inlets=1, outlets=1)

		if len(initargs):
			channel = initargs[0]
		else:
			channel = 0

		self.dsp_outputs = [0]
		self.dsp_init("adc~")
		self.dsp_setparam("channel", channel)


	def trigger(self):
		try:
			channel = int(self.inlets[0])
			self.set_param("channel", channel)
		except:
			print "Can't convert %s to a channel number" % self.inlet[0]
				

def register():
	MFPApp.register("adc~", ADC)
	MFPApp.register("dac~", DAC)


