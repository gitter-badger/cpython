#include "Python.h"

static PyMethodDef dtrace_methods[] = {
    {NULL,      NULL}
};


PyMODINIT_FUNC initdtrace(void)
{
    PyObject *mod, *v;

    mod = Py_InitModule("dtrace", dtrace_methods);
    if (!mod)
        return;

#ifdef WITH_DTRACE
    v = Py_True;
#else
    v = Py_False;
#endif

    Py_INCREF(v);
    if (PyModule_AddObject(mod, "available", v) < 0)
        return;
}
