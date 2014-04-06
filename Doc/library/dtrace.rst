:mod:`dtrace` --- DTrace probes for Python
===============================================

.. module:: dtrace
   :synopsis: DTrace probes for Python.

**Source code:** :source:`Lib/dtrace.py`

--------------

The :mod:`dtrace` module indicates if the CPython executable currently
running has been compiled with DTrace probes support.

.. impl-detail::

   DTrace probes are implementation details of the CPython interpreter!
   No garantees are made about probe compatibility between versions of
   CPython. DTrace scripts can stop working or work incorrectly without
   warning when changing CPython versions.

The :mod:`dtrace` module defines the following variable:


.. data:: available

   The variable will be ``True`` if the current CPython interpreter was
   compiled with DTrace probe support. ``False`` if not.
   

DTrace probes
-------------

DTrace scripts are run externally to CPython. DTrace probes export
selected events inside CPython interpreter in order to make them
accessible to external scripts.

The probes are exported through the "python" provider. The available
probes are defined in the file :file:`Include/pydtrace.d`.

To learn how to use DTrace, read `DTrace User Guide
<http://docs.oracle.com/cd/E19253-01/819-5488/>`_.

.. opcode:: function-entry (arg0, arg1, arg2)

   Fires when python code enters a new function. *arg0* is sourcecode
   file path, *arg1* is the name of the funcion called, and *arg2* is
   line number.

   The probe is not fired if Python code calls C functions.

.. opcode:: function-return (arg0, arg1, arg2)

   Fires when Python code finishes execution of a function. Parameters
   are the same as in ``function-entry``.

   The probe is not fired if the finishing function is written in C.

.. opcode:: line (arg0, arg1, arg2)

   Fires when Python code changes the execution line. Parameters are the
   same as in ``function-entry``.

   The probe is not fired in C functions.

.. opcode:: gc-start (arg0)

   Fires when the Python interpreter starts a garbage collection cycle.
   *arg0* is the generation to scan, like :func:`gc.collect()`.

.. opcode:: gc-done (arg0)

   Fires when the Python interpreter finishes a garbage collection
   cycle. *arg0* is the number of collected objects.

.. opcode:: instance-new-start (arg0, arg1)

   Fires when an object instanciation starts. *arg0* is the class name,
   *arg1* is the filename where the class is defined.

   The probe is not fired for most C code object creations.

.. opcode:: instance-new-done (arg0, arg1)

   Fires when an object instanciation finishes. Parameters are the same
   as in ``instance-new-done``.

   The probe is not fired for most C code object creations.

.. opcode:: instance-delete-start (arg0, arg1)

   Fires when an object instance is going to be destroyed. Parameters
   are the same as in ``instance-new-done``.

   The probe is not fired for most C code object destructions.

.. opcode:: instance-delete-done (arg0, arg1)

   Fires when an object instance has been destroyed. parameters are the
   same as in ``instance-new-done``.

   Between an ``instance-delete-start`` and corresponding
   ``instance-delete-done`` others probes can fire if, for instance,
   deletion of an instance creates a deletion cascade.

   The probe is not fired for most C code object destructions.


Python stack
------------

When a DTrace probe is fired, the DTrace script can examine the stack.
Since CPython is a Python interpreter coded in C, the stack will show C
functions, with no direct relation to the Python code currently being
executed.

Using the special "jstack()" DTrace function, the user will be given
hints about the python program stack, if possible. In particular, the
augmented stack will show python function calls, filename, name
of the function or method, and the line number.

DTrace scripts examples
-----------------------

DTrace python provider is suffixed by the pid of the process to monitor.
In the examples, the pid will be 9876.

Show the time spent doing garbage collection (in nanoseconds)::

  python9876:::gc-start
  {
      self->t = timestamp;
  }

  python9876:::gc-done
  /self->t/
  {
      printf("%d", timestamp-self->t);
      self->t = 0;
  }

Count how many instances are created of each class::

  python9876:::instance-new-start
  {
      @v[copyinstr(arg1), copyinstr(arg0)] = count();
  }

Observe time spent in object destruction, useful if datastructures are
complicated and deletion of an object can create a cascade effect::

  python9876:::instance-delete-start
  /self->t==0/
  {
      self->t = timestamp;
      self->level = 0;
  }

  python9876:::instance-delete-start
  /self->t/
  {
      self->level += 1;
  }

  python9876:::instance-delete-done
  /(self->level) && (self->t)/
  {
      self->level -= 1;
  }

  python9876:::instance-delete-done
  /(self->level==0) && (self->t)/
  {
      @time = quantize(timestamp-self->t);
      self->t = 0;
  }

To know which python source code lines create new TCP/IP connections::

  pid9876::sock_connect:entry
  {
      @conn[jstack()] = count();
  }

