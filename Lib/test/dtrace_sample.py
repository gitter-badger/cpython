# Sample script for use by test_dtrace.py
# DO NOT MODIFY THIS FILE IN ANY WAY WITHOUT UPDATING test_dtrace.py!!!!!

import gc

def function_1() :
    pass

# Check stacktrace
def function_2() :
    function_1()

# CALL_FUNCTION_VAR
def function_3(dummy, dummy2) :
    pass

# CALL_FUNCTION_KW
def function_4(**dummy) :
    pass

# CALL_FUNCTION_VAR_KW
def function_5(dummy, dummy2, **dummy3) :
    pass

def test_entry_return_and_stack() :
    function_1()
    function_2()
    function_3(*(1,2))
    function_4(**{"test":42})
    function_5(*(1,2), **{"test":42})

def test_line() :
    a = 1  # Preamble
    for i in xrange(2) :
        a = i
        b = i+2
        c = i+3
        d = a + b +c
    a = 1  # Epilogue

def test_instance_creation_destruction() :
    class old_style_class() :
        pass
    class new_style_class(object) :
        pass

    a = old_style_class()
    del a
    gc.collect()
    b = new_style_class()
    del b
    gc.collect()

    a = old_style_class()
    del old_style_class
    gc.collect()
    b = new_style_class()
    del new_style_class
    gc.collect()
    del a
    gc.collect()
    del b
    gc.collect()

def test_garbage_collection() :
    gc.collect()

if __name__ == "__main__":
    test_entry_return_and_stack()
    test_line()
    test_instance_creation_destruction()
    test_garbage_collection()

