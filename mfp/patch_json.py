#! /usr/bin/env python
'''
patch_json.py
Methods to save and load JSON patch data

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import simplejson as json
from .patch import Patch
from .utils import extends
from .bang import BangType, UninitType
from . import log 


class ExtendedEncoder (json.JSONEncoder):
    TYPES = { 'BangType': BangType, 'UninitType': UninitType }

    def default(self, obj):
        print "ExtendedEncoder:", obj, ExtendedEncoder.TYPES.values()
        if isinstance(obj, tuple(ExtendedEncoder.TYPES.values())):
            key = "__%s__" % obj.__class__.__name__
            return {key: obj.__dict__ }
        else:
            return json.JSONEncoder.default(obj)


def extended_decoder_hook (saved):
    if (isinstance(saved, dict) and len(saved.keys()) == 1):

        tname, tdict = saved.items()[0]
        key = tname.strip("_")
        ctor = ExtendedEncoder.TYPES.get(key)
        if ctor:
            return ctor.load(tdict)
    return saved 


@extends(Patch)
def json_deserialize(self, json_data):
    from main import MFPApp

    f = json.loads(json_data, object_hook=extended_decoder_hook)
    self.init_type = f.get('type')
    self.gui_params = f.get('gui_params', {})

    # clear old objects
    for o in self.objects.values():
        o.delete()
    self.objects = {}
    self.scopes = {}
    self.inlet_objects = []
    self.outlet_objects = []

    # create new objects
    idmap = {}
    idlist = f.get('objects').keys()
    idlist.sort(key=lambda x: int(x))
    for oid in idlist:
        prms = f.get('objects')[oid]

        otype = prms.get('type')
        oargs = prms.get('initargs')
        oname = prms.get('name')
        newobj = MFPApp().create(otype, oargs, self, self.default_scope, oname)

        if otype == 'inlet':
            self.inlet_objects.append(newobj)
        elif otype == 'outlet':
            self.outlet_objects.append(newobj)

        newobj.patch = self

        gp = prms.get('gui_params')
        for k, v in gp.items():
            newobj.gui_params[k] = v

        # custom behaviors implemented by Processor subclass load()
        newobj.load(prms)

        idmap[int(oid)] = newobj

    for oid, mfpobj in idmap.items():
        self.objects[mfpobj.obj_id] = mfpobj

    # load new scopes
    scopes = f.get("scopes", {})
    for scopename, bindings in scopes.items():
        s = self.add_scope(scopename)
        for name, oid in bindings.items():
            if name == "self":
                continue

            obj = idmap.get(oid)
            if obj is None:
                log.debug("Error in patch (object %d not found), continuing anyway" % oid)
                print "Error loading", scopename, oid
            else:
                s.bind(name, obj)
                obj.scope = s

    self.default_scope = self.scopes.get('__patch__') or self.add_scope("__patch__")
    self.default_scope.bind("self", self)

    # failsafe -- add un-scoped objects to default scope
    for oid, obj in self.objects.items():
        if obj.scope is None:
            self.default_scope.bind(obj.name, obj)
            obj.scope = self.default_scope

    # make connections
    for oid, prms in f.get('objects', {}).items():
        oid = int(oid)
        conn = prms.get("connections", [])
        srcobj = idmap.get(oid)
        for outlet in range(0, len(conn)):
            connlist = conn[outlet]
            for c in connlist:
                dstobj = idmap.get(c[0])
                inlet = c[1]
                srcobj.connect(outlet, dstobj, inlet)

    self.resize(len(self.inlet_objects), len(self.outlet_objects))


@extends(Patch)
def json_serialize(self):
    f = {}
    f['type'] = self.init_type
    f['gui_params'] = self.gui_params

    allobj = {}
    keys = self.objects.keys()
    keys.sort()
    for oid in keys:
        o = self.objects.get(oid)
        oinfo = o.save()
        allobj[oid] = oinfo

    f['objects'] = allobj

    scopes = {}
    for scopename, scope in self.scopes.items():
        bindings = {}
        for objname, obj in scope.bindings.items():
            bindings[objname] = obj.obj_id

        scopes[scopename] = bindings

    f['scopes'] = scopes
    return json.dumps(f, indent=4, cls=ExtendedEncoder)
