#! /usr/bin/env python2.6
'''
slider.py: SliderEdit and SliderControl major modes 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from mfp import log 

class SliderBaseMode (InputMode):
	def __init__(self, window, element, descrip):
		self.manager = window.input_mgr
		self.window = window 
		self.slider = element

		self.drag_started = True
		self.drag_start_x = self.manager.pointer_x
		self.drag_start_y = self.manager.pointer_y
		self.drag_last_x = self.manager.pointer_x
		self.drag_last_y = self.manager.pointer_y

		InputMode.__init__(self, descrip)

		self.bind("M1DOWN", self.drag_start, "slider-drag-start")
		self.bind("M1-MOTION", lambda: self.drag_selected(1.0), "slider-drag-selected-1")
		self.bind("S-M1-MOTION", lambda: self.drag_selected(0.25), "slider-drag-selected-.25")
		self.bind("C-M1-MOTION", lambda: self.drag_selected(0.05), "slider-drag-selected-.05")
		self.bind("M1UP", self.drag_end, "patch-drag-end")

	def drag_start(self):
		if self.manager.pointer_obj == self.slider:
			if self.window.selected != self.slider:
				self.window.select(self.slider)

			if self.slider.point_in_slider(self.manager.pointer_x, self.manager.pointer_y):
				log.debug("sliderbasemode: starting drag")
				self.drag_started = True
				self.drag_start_x = self.manager.pointer_x
				self.drag_start_y = self.manager.pointer_y
				self.drag_last_x = self.manager.pointer_x
				self.drag_last_y = self.manager.pointer_y
			return True
		else:
			return False

	def drag_selected(self, delta=1.0):
		if self.drag_started is False:
			return False

		dx = self.manager.pointer_x - self.drag_last_x
		dy = self.manager.pointer_y - self.drag_last_y 
		
		self.drag_last_x = self.manager.pointer_x
		self.drag_last_y = self.manager.pointer_y 
			
		value_change = self.slider.pixdelta2value(delta*dy)

		self.slider.update_value(self.slider.value - value_change)
		return True

	def drag_end(self):
		if self.drag_started:
			self.drag_started = False
			return True
		else:
			return False


class SliderControlMode (SliderBaseMode):
	pass

class SliderEditMode (SliderBaseMode):
	pass
