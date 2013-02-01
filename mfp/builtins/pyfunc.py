#! /usr/bin/env python2.6
'''
p_pyfunc.py: Wrappers for common unary and binary Python functions

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from ..evaluator import Evaluator
from ..method import MethodCall
from ..bang import Bang, Uninit


class ApplyMethod(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        self.method_name = None

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.method_name = initargs[0]

    def trigger(self):
        if self.inlets[0] is Bang:
            self.outlets[0] = MethodCall(self.method_name)
        else:
            self.outlets[0] = MethodCall(self.method_name, *(self.inlets[0]))


class GetElement(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.element = initargs[0]

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.element = self.inlets[1]

        if self.element is None:
            return

        if isinstance(self.element, (int, float)):
            self.outlets[0] = self.inlets[0][int(self.element)]
        elif isinstance(self.inlets[0], dict):
            self.outlets[0] = self.inlets[0].get(self.element)
        else:
            self.outlets[0] = getattr(self.inlets[0], self.element)

        self.outlets[1] = self.inlets[0]


class PyEval(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        self.bindings = {}

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.bindings = initargs[0]

    def trigger(self):
        if isinstance(self.inlets[0], MethodCall):
            self.inlets[0].call(self)
        else:
            self.outlets[0] = self.patch.eval(self.inlets[0], self.bindings)

    def clear(self):
        self.bindings = {}

    def bind(self, **kwargs):
        for name, value in kwargs.items():
            self.bindings[name] = value

class PyFunc(Processor): 
    def __init__(self, init_type, init_args, patch, scope, name):
        if init_args:
            thunktxt = "lambda " + init_args
        else:
            thunktxt = "lambda: None"

        self.thunk = patch.parse_obj(thunktxt)
        
        if callable(self.thunk):
            self.argcount = self.thunk.func_code.co_argcount
        Processor.__init__(self, self.argcount, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        if isinstance(self.inlets[0], MethodCall):
            self.inlets[0].call(self)
        else:
            self.outlets[0] = self.thunk(*[i for i in self.inlets if i is not Uninit]) 

class PyAutoWrap(Processor): 
    def __init__(self, init_type, init_args, patch, scope, name):
        self.thunk = patch.parse_obj(init_type)
        initargs, kwargs = patch.parse_args(init_args)
        
        if callable(self.thunk):
            self.argcount = self.thunk.func_code.co_argcount
        Processor.__init__(self, self.argcount, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        if isinstance(self.inlets[0], MethodCall):
            self.inlets[0].call(self)
        else:
            self.outlets[0] = self.thunk(*[i for i in self.inlets if i is not Uninit]) 

class PyBinary(Processor):
    def __init__(self, pyfunc, init_type, init_args, patch, scope, name):
        self.function = pyfunc
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs) == 1:
            self.inlets[1] = initargs[0]

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.outlets[0] = self.function(self.inlets[0], self.inlets[1])
        else:
            # hope for a default
            self.outlets[0] = self.function(self.inlets[0])

class PyUnary(Processor):
    def __init__(self, pyfunc, init_type, init_args, patch, scope, name):
        self.function = pyfunc
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        self.outlets[0] = self.function(self.inlets[0])

class PyNullary(Processor):
    def __init__(self, pyfunc, init_type, init_args, patch, scope, name):
        self.function = pyfunc
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        self.outlets[0] = self.function()


def mk_nullary(pyfunc, name):
    def factory(iname, args, patch, scope, obj_name):
        proc = PyNullary(pyfunc, iname, args, patch, scope, obj_name)
        return proc
    MFPApp().register(name, factory)

def mk_binary(pyfunc, name):
    def factory(iname, args, patch, scope, obj_name):
        proc = PyBinary(pyfunc, iname, args, patch, scope, obj_name)
        return proc
    MFPApp().register(name, factory)


def mk_unary(pyfunc, name):
    def factory(iname, args, patch, scope, obj_name):
        proc = PyUnary(pyfunc, iname, args, patch, scope, obj_name)
        return proc
    MFPApp().register(name, factory)

import operator
import math
import cmath

def make_date(args):
    import datetime

    if isinstance(args, datetime.datetime):
        return args.date()
    else:
        return datetime.date(*args)

def applyargs(func):
    def wrapped(args):
        return func(*args)
    return wrapped


def register():
    MFPApp().register("get", GetElement)
    MFPApp().register("eval", PyEval)
    MFPApp().register("apply", ApplyMethod)
    MFPApp().register("func", PyFunc)

    mk_binary(operator.add, "+")
    mk_binary(operator.sub, "-")
    mk_binary(operator.mul, "*")
    mk_binary(operator.div, "/")
    mk_binary(operator.mod, "%")
    mk_binary(operator.pow, "^")
    mk_binary(operator.pow, "**")

    mk_unary(math.log, "log")
    mk_unary(math.exp, "exp")
    mk_unary(math.log10, "log10")
    mk_binary(math.pow, "pow")

    mk_unary(math.sin, "sin")
    mk_unary(math.cos, "cos")
    mk_unary(math.tan, "tan")
    mk_unary(math.acos, "acos")
    mk_unary(math.asin, "asin")
    mk_binary(math.atan2, "atan2")

    mk_binary(operator.gt, ">")
    mk_binary(operator.lt, "<")
    mk_binary(operator.ge, ">=")
    mk_binary(operator.le, "<=")
    mk_binary(operator.eq, "==")
    mk_binary(operator.ne, "!=")

    mk_unary(abs, "abs")
    mk_unary(operator.neg, "neg")
    mk_unary(cmath.phase, "phase")

    # type converters
    mk_binary(complex, "complex")
    mk_unary(int, "int")
    mk_unary(float, "float")
    mk_unary(tuple, "tuple")
    mk_unary(list, "list")
    mk_unary(type, "type")
    mk_unary(dict, "dict")

    from datetime import datetime 
    mk_nullary(datetime.now, "now")
    mk_unary(applyargs(datetime), "datetime")
    mk_unary(make_date, "date")

