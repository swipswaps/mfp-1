#! /usr/bin/env python
'''
plugin.py: Builtin plugin host
Currently only LADSPA 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp 
from ..bang import Uninit 

class Plugin(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = patch.parse_args(init_args)
    
        self.lib_name = None
        self.lib_index = None 
        self.plug_name = None 
        self.plug_inlets = 0
        self.plug_outlets = 0
        self.plug_control = []
        self.dsp_inlets = []
        self.dsp_outlets = [] 

        if len(initargs):
           self.init_plugin(initargs[0])

        Processor.__init__(self, self.plug_inlets, self.plug_outlets, init_type, init_args, 
                           patch, scope, name)
        self.hot_inlets = range(self.plug_inlets)
        self.dsp_init("ladspa~", lib_name=self.lib_name, lib_index=self.lib_index,
                      plug_control=self.plug_control)

    def init_plugin(self, pname): 

        pinfo = MFPApp().pluginfo.find(pname)

        self.lib_name = pinfo.get("lib_name")
        self.lib_index = pinfo.get("lib_index")
        self.plug_name = pinfo.get("label")

        portinfo = pinfo.get("ports", [])

        for portnum, port in enumerate(portinfo):
            self.plug_control.append(0) 

            d = port.get("descriptor", 0)
            if d & MFPApp().pluginfo.LADSPA_PORT_INPUT:
                if d & MFPApp().pluginfo.LADSPA_PORT_AUDIO:
                    self.dsp_inlets.extend([self.plug_inlets])
                else:
                    self.plug_control[portnum] = MFPApp().pluginfo.port_default(port)
                self.plug_inlets += 1

            elif d & MFPApp().pluginfo.LADSPA_PORT_OUTPUT:
                if d & MFPApp().pluginfo.LADSPA_PORT_AUDIO:
                    self.dsp_outlets.extend([self.plug_outlets])
                else:
                    self.plug_control[portnum] = MFPApp().pluginfo.port_default(port)
                self.plug_outlets += 1

    def trigger(self): 
        for portnum, value in enumerate(self.inlets):
            if value is not Uninit:
                self.plug_control[portnum] = float(value)
        self.dsp_setparam("plug_control", self.plug_control)

def register():
   MFPApp().register("plugin~", Plugin)

