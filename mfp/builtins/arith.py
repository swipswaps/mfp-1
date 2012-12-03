#! /usr/bin/env python2.6
'''
arith.py:  Builtin arithmetic DSP ops

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class ArithProcessor(Processor):
	def __init__(self, init_type, init_args, arith_op):
		self.arith_op = init_type

		Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

		
		self.dsp_inlets = [0, 1]
		self.dsp_outlets = [0]
		self.dsp_init(self.arith_op)
		
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs):
			self.dsp_obj.setparam("const", initargs[0])
		

	def trigger(self):
		try:
			val = float(self.inlets[0])
			self.dsp_obj.setparam("const", val)
		except:
			print "Can't convert %s to a value" % self.inlet[0]
				

class ArithAdd(ArithProcessor):
	def __init__(self, init_type, init_args, patch, scope, name):
		ArithProcessor.__init__(self, init_type, init_args, patch, scope, name)

class ArithSub(ArithProcessor):
	def __init__(self, init_type, init_args, patch, scope, name):
		ArithProcessor.__init__(self, init_type, init_args, patch, scope, name)

class ArithMul(ArithProcessor):
	def __init__(self, init_type, init_args, patch, scope, name):
		ArithProcessor.__init__(self, init_type, init_args, patch, scope, name)

class ArithDiv(ArithProcessor):
	def __init__(self, init_type, init_args, patch, scope, name):
		ArithProcessor.__init__(self, init_type, init_args, patch, scope, name)

def register():
	MFPApp().register("+~", ArithAdd)
	MFPApp().register("-~", ArithSub)
	MFPApp().register("*~", ArithMul)
	MFPApp().register("/~", ArithDiv)

