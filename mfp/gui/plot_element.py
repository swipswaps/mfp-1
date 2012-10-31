#! /usr/bin/env python
'''
plot_element.py
A patch element corresponding to an XY scatter or line plot 
'''

from gi.repository import Clutter as clutter 
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from input_mode import InputMode
from .modes.label_edit import LabelEditMode
from .xyplot import XYPlot

class PlotElement (PatchElement):
	element_type = "plot"

	# constants 
	INIT_WIDTH = 320
	INIT_HEIGHT = 240
	LABEL_SPACE = 25
	label_off_x = 6 
	label_off_y = 0

	def __init__(self, window, x, y, params={}):
		PatchElement.__init__(self, window, x, y)
		
		# display elements 
		self.rect = None
		self.label = None
		self.label_text = None 
		self.xyplot = None

		# display bounds 
		self.x_min = 0.0
		self.x_max = 6.28
		self.y_min = -1.0
		self.y_max = 1.0

		# grab params for creation

		# create display 
		self.create_display(self.INIT_WIDTH+6, self.INIT_HEIGHT+self.LABEL_SPACE+4)
		self.move(x, y)
		self.update()

	def create_display(self, width, height):
		print "chart_element: create_display", width, height
		self.rect = clutter.Rectangle()
		self.label = clutter.Text()

		# group
		clutter.Group.set_size(self, width, height)

		# rectangle box 
		self.rect.set_border_width(2)
		self.rect.set_border_color(self.stage.color_unselected)
		self.rect.set_position(0,0)
		self.rect.set_size(width, height)
		self.rect.set_depth(-1)
		self.rect.set_reactive(False)

		# label
		self.label.set_position(self.label_off_x, self.label_off_y)
		self.label.set_color(self.stage.color_unselected) 
		self.label.connect('text-changed', self.label_changed_cb)
		self.label.set_reactive(False)

		# chart
		self.xyplot = XYPlot(self.INIT_WIDTH, self.INIT_HEIGHT)
		self.xyplot.set_position(3, self.LABEL_SPACE)

		self.add_actor(self.xyplot)
		self.add_actor(self.label)
		self.add_actor(self.rect)
		self.set_reactive(True)

	# methods useful for interaction
	def set_bounds(self, x_min, y_min, x_max, y_max):
		print "bounds:",  x_min, y_min, x_max, y_max
		self.x_min = x_min
		self.x_max = x_max
		self.y_min = y_min
		self.y_max = y_max

		self.xyplot.set_bounds(x_min, y_min, x_max, y_max)
	

	def update(self):
		self.draw_ports()

	def get_label(self):
		return self.label

	def label_edit_start(self):
		# FIXME set label to editing style 
		pass

	def label_edit_finish(self, *args):
		t = self.label.get_text()

		if t != self.label_text:
			parts = t.split(' ', 1)
			self.obj_type = parts[0]
			if len(parts) > 1:
				self.obj_args = parts[1]

			print "PlotElement: type=%s, args=%s" % (self.obj_type, self.obj_args)
			self.create(self.element_type, self.obj_args)
			
			if self.obj_type == "scatter":
				self.xyplot.mode = XYPlot.SCATTER
			elif self.obj_type == "line":
				self.xyplot.mode = XyPlot.LINE
			elif self.obj_type == "roll":
				self.xyplot.mode = XyPlot.ROLL
			elif self.obj_type == "scope":
				self.xyplot.mode = XyPlot.SCOPE

			if self.obj_id is None:
				print "PlotElement: could not create", self.obj_type, self.obj_args
			else:
				self.send_params()
				self.draw_ports()

		# FIXME set label to non-editing style 

		self.update()

	def label_changed_cb(self, *args):
		pass

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		clutter.Group.set_position(self, x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def set_size(self, w, h):
		print "chart_element: set_size", w, h
		self.size_w = w
		self.size_h = h 

		self.rect.set_size(w, h)
		self.rect.set_position(0, 0)
		self.xyplot.set_size(w-4, h-self.LABEL_SPACE-4)

		clutter.Group.set_size(self, w, h)

		self.draw_ports()

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def select(self):
		self.selected = True 
		self.rect.set_border_color(self.stage.color_selected)

	def unselect(self):
		self.selected = False 
		self.rect.set_border_color(self.stage.color_unselected)

	def delete(self):
		for c in self.connections_out+self.connections_in:
			c.delete()

		PatchElement.delete(self)

	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.label)

	def configure(self, params):
		if self.obj_args is None:
			self.label.set_text("%s" % (self.obj_type,))
		else:
			self.label.set_text("%s %s" % (self.obj_type, self.obj_args))

		action = params.get("_chart_action")
		if action == "clear":
			curve = params.get("_chart_data")
			self.xyplot.clear(curve)
		elif action == "add":
			newpts = params.get("_chart_data")
			for c in newpts:
				for p in newpts[c]:
					self.xyplot.append(p, c)
		elif action == "bounds":
			bounds = params.get("_chart_data")
			self.set_bounds(*bounds)
		elif action == "roll":
			start_x = params.get("_chart_data")
			self.xyplot.set_bounds(None, None, start_x, None)
			self.xyplot.set_scroll_rate(1.0, 0)
		elif action == "stop":
			self.xyplot.set_scroll_rate(0.0, 0.0)
		elif action == "reset":
			start_x = params.get("_chart_data")
			self.xyplot.set_bounds(None, None, start_x, None)

		s = params.get("style")
		if s:
			self.xyplot.set_style(s)
			
		PatchElement.configure(self, params)	
