
from unittest import TestCase
from mfp.patch import Patch
from mfp.main import MFPApp

import simplejson as json

jsdata_1 = '''
{"objects": {
"0": {"connections": [[]], "initargs": "True", "type": "var", 
	"gui_params": {"element_type": "message", "position_x": 118.0, "position_y": 423.0}}, 
"1": {"connections": [[]], "initargs": "False", "type": "var", 
	"gui_params": {"element_type": "message", "position_x": 204.0, "position_y": 424.0}}, 
"2": {"connections": [[]], "initargs": "0", "type": "var", 
	"gui_params": {"element_type": "enum", "position_x": 327.0, "position_y": 263.0}}, 
"3": {"connections": [[]], "initargs": "", "type": "var", 
	"gui_params": {"message_text": "HIGH", "element_type": "text", "position_x": 386.0, "position_y": 162.0}}, 
"4": {"connections": [[]], "initargs": "", "type": "var", 
	"gui_params": {"message_text": "LOW", "element_type": "text", "position_x": 389.0, "position_y": 363.0}}, 
"5": {"connections": [[]], "initargs": "", "type": "var", 
	"gui_params": {"message_text": "test-enum-gui.mfp", "element_type": "text", "position_x": 22.0, "position_y": 28.0}}}, 
"name": "Default"}
'''

class PatchTests (TestCase):
	def setUp(self):
		MFPApp().no_gui = True		
		MFPApp().next_obj_id = 0 
		MFPApp().objects = {}
		self.patch = Patch()
		pass

	def test_loadsave(self):
		self.patch.load_string(jsdata_1)
		self.assertEqual(json.loads(jsdata_1), json.loads(self.patch.save_string()))

