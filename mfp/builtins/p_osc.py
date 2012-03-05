#! /usr/bin/env python2.6
'''
p_osc.py:  Builtin oscillator DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class Osc(Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 3, 1, init_type, init_args)
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs):
			freq = initargs[0]
		else:
			freq = 0

		self.dsp_inlets = [1, 2]
		self.dsp_outlets = [0]
		self.dsp_init("osc", _sig_1=float(freq))

	def trigger(self):
		# number inputs to the DSP ins (freq, amp) are
		# handled automatically
		if self.inlets[0] is Bang:
			self.set_param("phase", float(0))
		else:
			try:
				phase = float(self.inlets[0])
				self.set_param("phase", phase)
			except:
				print "Can't convert %s to a frequency value" % self.inlets[0]
				
def register():
	MFPApp().register("osc~", Osc)

