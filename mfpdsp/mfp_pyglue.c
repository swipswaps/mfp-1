
#include <Python.h>
#include <pthread.h>
#include <signal.h>
#include <execinfo.h>
#include "mfp_dsp.h"
#include "builtin.h"


static PyObject * 
dsp_startup(PyObject * mod, PyObject * args) 
{
    int num_inputs, num_outputs;
    PyArg_ParseTuple(args, "ii", &num_inputs, &num_outputs);

    mfp_jack_startup(num_inputs, num_outputs);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
dsp_shutdown(PyObject * mod, PyObject * args) 
{
    mfp_jack_shutdown();
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
dsp_enable(PyObject * mod, PyObject * args)
{
    mfp_dsp_enabled = 1;
    Py_INCREF(Py_True);
    return Py_True;
}

static PyObject *
dsp_disable(PyObject * mod, PyObject * args)
{
    mfp_dsp_enabled = 0;
    Py_INCREF(Py_True);
    return Py_True;
}

static PyObject * 
dsp_samplerate(PyObject * mod, PyObject * args)
{
    PyObject * rval = PyFloat_FromDouble((double)mfp_samplerate);
    Py_INCREF(rval);
    return rval;
}
static PyObject * 
dsp_blocksize(PyObject * mod, PyObject * args)
{
    PyObject * rval = PyFloat_FromDouble((double)mfp_blocksize);
    Py_INCREF(rval);
    return rval;
}


static PyObject *
dsp_response_wait(PyObject * mod, PyObject * args)
{
    int responses = 0;
    PyObject * l = NULL;
    PyObject * t;
    PyObject * proc;
    mfp_respdata r;
    int rcount;

    Py_BEGIN_ALLOW_THREADS
    pthread_mutex_lock(&mfp_response_lock);
    if (!mfp_responses_pending || (mfp_responses_pending->len == 0)) {
        pthread_cond_wait(&mfp_response_cond, &mfp_response_lock);
    }
    Py_END_ALLOW_THREADS

    /* copy/clear C response objects */
    if(mfp_responses_pending && (mfp_responses_pending->len > 0)) {
        l = PyList_New(mfp_responses_pending->len);
        for(rcount=0; rcount < mfp_responses_pending->len; rcount++) {
            t = PyTuple_New(3);
            r = g_array_index(mfp_responses_pending, mfp_respdata, rcount);

            proc = g_hash_table_lookup(mfp_proc_objects, r.dst_proc);
            if (proc == NULL)
                continue;

            Py_INCREF(proc);

            PyTuple_SetItem(t, 0, proc);
            PyTuple_SetItem(t, 1, PyInt_FromLong(r.msg_type));
            switch(r.response_type) {
                case PARAMTYPE_FLT:
                    PyTuple_SetItem(t, 2, PyFloat_FromDouble(r.response.f));
                    break;
                case PARAMTYPE_BOOL:
                    PyTuple_SetItem(t, 2, PyBool_FromLong(r.response.i));
                    break;
                case PARAMTYPE_INT:
                    PyTuple_SetItem(t, 2, PyInt_FromLong(r.response.i));
                    break;
                case PARAMTYPE_STRING:
                    PyTuple_SetItem(t, 2, PyString_FromString(r.response.c));
                    g_free(r.response.c);
                    break;
            }
            PyList_SetItem(l, rcount, t);
            responses += 1;
        }
        g_array_remove_range(mfp_responses_pending, 0, mfp_responses_pending->len);
    }
    pthread_mutex_unlock(&mfp_response_lock);


    /* build python response */

    if (responses == 0) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else {
        Py_INCREF(l);
        return l;
    }
}

static int
set_c_param(mfp_processor * proc, char * paramname, PyObject * val) 
{
    int rval = 1;
    int vtype = (int)g_hash_table_lookup(proc->typeinfo->params, paramname);    
    float cflt;
    int cint;
    char * cstr;
    int llen, lpos;
    GArray * g;
    PyObject * oldval;
    PyObject * listval;

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            printf("set_c_param: undefined parameter %s\n", paramname);
            rval = 0;
            break;
        case PARAMTYPE_FLT:
            if (PyNumber_Check(val)) {
                cflt = PyFloat_AsDouble(PyNumber_Float(val));
                mfp_proc_setparam_float(proc, paramname, cflt);
            }
            else {
                rval = 0;
            }
            break;

        case PARAMTYPE_INT:
            if (PyNumber_Check(val)) {
                cint = (int)PyFloat_AsDouble(PyNumber_Float(val));
                mfp_proc_setparam_float(proc, paramname, cint);
            }
            else {
                rval = 0;
            }
            break;

        case PARAMTYPE_STRING:
            if (PyString_Check(val)) {
                cstr = PyString_AsString(val);
                mfp_proc_setparam_string(proc, paramname, cstr);
            }
            else {
                rval = 0;
            }
            break;

        case PARAMTYPE_FLTARRAY:
            if (PyList_Check(val)) {
                llen = PyList_Size(val);
                g = g_array_sized_new(FALSE, FALSE, sizeof(float), llen);
                for(lpos=0; lpos < llen; lpos++) {
                    listval = PyList_GetItem(val, lpos);
                    if (PyNumber_Check(listval)) {
                        cflt = (float)PyFloat_AsDouble(PyNumber_Float(listval));
                        g_array_append_val(g, cflt); 
                    }
                    else {
                        rval = 0;
                    }
                }
                if (rval == 1) 
                    mfp_proc_setparam_array(proc, paramname, g);
                else {
                    g_array_free(g, TRUE);
                }
            }
            else {
                rval = 0;
            }
            break;
    }
    if (rval != 0) {
        oldval = g_hash_table_lookup(proc->pyparams, paramname);
        if (oldval != NULL) {
            Py_DECREF(oldval);
        }
        Py_INCREF(val);
        g_hash_table_replace(proc->pyparams, g_strdup(paramname), val);

        /* FIXME: race on setting needs_config */ 
        proc->needs_config = 1;
    }

    return rval;
}


static int
extract_c_params(mfp_processor * proc, PyObject * params)
{
    PyObject *key, *value;
    Py_ssize_t pos = 0;
    char * param_name;
    int retval = 1;

    while(PyDict_Next(params, &pos, &key, &value)) {
        param_name = PyString_AsString(key);
        retval = set_c_param(proc, param_name, value);
        if (retval == 0) 
            return retval;
    }
    return retval;
}



static PyObject * 
proc_create(PyObject * mod, PyObject *args)
{
    /* args are processor typename and param dict */ 
    char     * typestr = NULL;
    int num_inlets, num_outlets;
    PyObject * paramdict;
    PyObject * newobj;
    PyArg_ParseTuple(args, "siiO", &typestr, &num_inlets, &num_outlets, &paramdict); 

    mfp_procinfo * pinfo = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, typestr);
    mfp_processor * proc;

    if (pinfo == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else {
        proc = mfp_proc_alloc(pinfo, num_inlets, num_outlets, mfp_blocksize);
        extract_c_params(proc, paramdict);
        mfp_proc_init(proc);

        newobj = PyCObject_FromVoidPtr(proc, NULL);
        Py_INCREF(newobj);

        g_hash_table_insert(mfp_proc_objects, proc, newobj);
        Py_INCREF(newobj);
        return newobj;
    }
}

static PyObject *
proc_destroy(PyObject * mod, PyObject * args)
{
    PyObject * self=NULL;
    PyObject * objref;
    mfp_reqdata rd;

    PyArg_ParseTuple(args, "O", &self);
    rd.reqtype = REQTYPE_DESTROY;
    rd.src_proc = PyCObject_AsVoidPtr(self);
    
    pthread_mutex_lock(&mfp_globals_lock);
    g_array_append_val(mfp_requests_pending, rd);
    pthread_mutex_unlock(&mfp_globals_lock);

    objref = (PyObject *)g_hash_table_lookup(mfp_proc_objects, rd.src_proc);
    Py_DECREF(objref);
    g_hash_table_remove(mfp_proc_objects, rd.src_proc);

    Py_INCREF(Py_False);
    return Py_False; 
}

static PyObject *
proc_connect(PyObject * mod, PyObject * args)
{
    PyObject * src =NULL;
    PyObject * srcport = NULL;
    PyObject * dst =NULL;
    PyObject * dstport = NULL;

    mfp_reqdata rd;

    PyArg_ParseTuple(args, "OOOO", &src, &srcport, &dst, &dstport);

    rd.reqtype = REQTYPE_CONNECT;
    rd.src_proc = PyCObject_AsVoidPtr(src);
    rd.src_port = (int)PyFloat_AsDouble(srcport);
    rd.dest_proc = PyCObject_AsVoidPtr(dst);
    rd.dest_port = (int)PyFloat_AsDouble(dstport);
    
    pthread_mutex_lock(&mfp_globals_lock);
    g_array_append_val(mfp_requests_pending, rd);
    pthread_mutex_unlock(&mfp_globals_lock);

    Py_INCREF(Py_False);
    return Py_False; 
}

static PyObject *
proc_disconnect(PyObject * mod, PyObject * args)
{
    PyObject * src =NULL;
    PyObject * srcport = NULL;
    PyObject * dst =NULL;
    PyObject * dstport = NULL;

    mfp_reqdata rd;

    PyArg_ParseTuple(args, "OOOO", &src, &srcport, &dst, &dstport);
    rd.reqtype = REQTYPE_DISCONNECT;
    rd.src_proc = PyCObject_AsVoidPtr(src);
    rd.src_port = (int)PyFloat_AsDouble(srcport);
    rd.dest_proc = PyCObject_AsVoidPtr(dst);
    rd.dest_port = (int)PyFloat_AsDouble(dstport);
    
    pthread_mutex_lock(&mfp_globals_lock);
    g_array_append_val(mfp_requests_pending, rd);
    pthread_mutex_unlock(&mfp_globals_lock);

    Py_INCREF(Py_False);
    return Py_False; 
}

static PyObject * 
proc_getparam(PyObject * mod, PyObject * args) 
{
    PyObject * self=NULL;
    PyObject * retval = NULL;
    char * param_name=NULL;

    PyArg_ParseTuple(args, "Os", &self, &param_name);
    retval = g_hash_table_lookup(((mfp_processor *)PyCObject_AsVoidPtr(self))->pyparams, param_name);
    if (retval == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else {
        return retval;
    }
}

static PyObject * 
proc_setparam(PyObject * mod, PyObject * args) 
{
    PyObject * self=NULL;
    char * param_name=NULL;
    PyObject * param_value = NULL;
    mfp_processor * p = NULL;

    PyArg_ParseTuple(args, "OsO", &self, &param_name, &param_value);
    p = (mfp_processor *)PyCObject_AsVoidPtr(self); 
    set_c_param(p, param_name, param_value);

    if(p->typeinfo->preconfig) {
        p->typeinfo->preconfig(p);
    }
    Py_INCREF(Py_False);
    return Py_False;
}

static PyObject * 
proc_reset(PyObject * mod, PyObject * args) 
{
    PyObject * self=NULL;

    PyArg_ParseTuple(args, "O", &self);
    mfp_proc_reset((mfp_processor *)PyCObject_AsVoidPtr(self));
    Py_INCREF(Py_None);
    return Py_None;

}


static PyMethodDef MfpDspMethods[] = {
    { "dsp_startup",  dsp_startup, METH_VARARGS, "Start processing thread" },
    { "dsp_shutdown",  dsp_shutdown, METH_VARARGS, "Stop processing thread" },
    { "dsp_enable",  dsp_enable, METH_VARARGS, "Enable dsp" },
    { "dsp_disable",  dsp_disable, METH_VARARGS, "Disable dsp" },
    { "dsp_samplerate",  dsp_samplerate, METH_VARARGS, "Return samplerate" },
    { "dsp_blocksize",  dsp_blocksize, METH_VARARGS, "Return blocksize" },
    { "dsp_response_wait",  dsp_response_wait, METH_VARARGS, "Return next DSP responses" },
    { "proc_create", proc_create, METH_VARARGS, "Create DSP processor" },
    { "proc_destroy", proc_destroy, METH_VARARGS, "Destroy DSP processor" },
    { "proc_connect", proc_connect, METH_VARARGS, "Connect DSP processors" },
    { "proc_disconnect", proc_disconnect, METH_VARARGS, "Disconnect DSP processors" },
    { "proc_getparam", proc_getparam, METH_VARARGS, "Get processor parameter" },
    { "proc_setparam", proc_setparam, METH_VARARGS, "Set processor parameter" },
    { "proc_reset", proc_reset, METH_VARARGS, "Reset processor state" },
    { NULL, NULL, 0, NULL}
};


static void
init_globals(void)
{
    mfp_proc_list = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
    mfp_proc_registry = g_hash_table_new(g_str_hash, g_str_equal);
    mfp_proc_objects = g_hash_table_new(NULL, NULL);
    mfp_requests_pending = g_array_new(TRUE, TRUE, sizeof(mfp_reqdata));
    mfp_responses_pending = g_array_new(TRUE, TRUE, sizeof(mfp_respdata));

    pthread_cond_init(&mfp_response_cond, NULL);
    pthread_mutex_init(&mfp_response_lock, NULL);
    pthread_mutex_init(&mfp_globals_lock, NULL);

}

#define ARRAY_LEN(arry, eltsize) (sizeof(arry) / eltsize)

static void
init_builtins(void)
{
    int i;
    mfp_procinfo * pi;
    mfp_procinfo * (* initfuncs[])(void) = { 
        init_builtin_osc, init_builtin_in, init_builtin_out, 
        init_builtin_sig, init_builtin_snap, init_builtin_ampl, 
        init_builtin_add, init_builtin_sub, init_builtin_mul, init_builtin_div, 
        init_builtin_lt, init_builtin_gt,
        init_builtin_line, init_builtin_noise, init_builtin_buffer,
        init_builtin_biquad, init_builtin_phasor,
        init_builtin_ladspa
    };
    int num_initfuncs = ARRAY_LEN(initfuncs, sizeof(mfp_procinfo *(*)(void)));

    printf("init_builtins: initializing %d builtin DSP processors\n", num_initfuncs);

    for(i = 0; i < num_initfuncs; i++) {
        pi = initfuncs[i]();
        g_hash_table_insert(mfp_proc_registry, pi->name, pi);
    }

}

int
test_SETUP(void) 
{
    /* called before each test case, where each test case is run 
     * in a separate executable */
    init_globals();
    init_builtins();
    return 0;
}

int 
benchmark_SETUP(void) 
{
    return test_SETUP();
}

int
test_TEARDOWN(void)
{
    return 0;
}


static void
sigsegv_handler(int sig, siginfo_t *si, void *unused)
{
    void * buffer[100];
    char ** strings;
    int nptrs, j;

    printf("ERROR: SIGSEGV received\n");
    nptrs = backtrace(buffer, 100);
    strings = backtrace_symbols(buffer, nptrs);

    for (j = 0; j < nptrs; j++)
        printf("%s\n", strings[j]);

    free(strings);

    exit(-11);
}


PyMODINIT_FUNC
initmfpdsp(void) 
{
    struct sigaction sa;

    /* install signal handlers */
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sa.sa_sigaction = sigsegv_handler;
    if (sigaction(SIGSEGV, &sa, NULL) == -1) {
        printf("testext ERROR: could not install SIGSEGV handler, exiting\n");
    }

    init_globals();
    init_builtins();
    Py_InitModule("mfpdsp", MfpDspMethods);
}

