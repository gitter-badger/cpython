import sys, unittest, subprocess, os.path, dis, types, re
import dtrace
from test.test_support import TESTFN, run_unittest, findfile

sample = os.path.abspath(findfile("dtrace_sample.py"))
if not dtrace.available :
    raise unittest.SkipTest, "dtrace support not compiled in"

def normalize(data) :
    # DTRACE keeps a per-CPU buffer, and when showing the fired probes,
    # buffers are concatenated. So if the operating system moves our
    # thread around, the straight result can be "non causal".
    # So we add timestamps to the probe firing, and sort by that field.

    # When compiling with '--with-pydebug'
    data = "".join(re.split("\[[0-9]+ refs\]", data))

    try :
        result = [i.split("\t") \
                for i in data.replace("\r", "").split("\n") if len(i)]
        result.sort(key = lambda i: int(i[0]))
        result = "".join((i[1] for i in result))
        result = result.replace(" ", "")
    except :
        # If something goes wrong, rebuild the value so we can see the
        # real result when the assert fails.
        result = data.replace("\r", "").replace("\n", "")
    return result

dscript = """
pid$target::PyEval_EvalCode:entry
"""
dscript = dscript.replace("\r", "").replace("\n", "")
result, _ = subprocess.Popen(["dtrace", "-q", "-l", "-n", dscript,
    "-c", "%s %s" %(sys.executable, sample)], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT).communicate()
if result.split("\n")[1].split()[-2:] != ["PyEval_EvalCode", "entry"] :
    result2 = repr(result)
    raise unittest.SkipTest("dtrace seems not to be working. " + \
        "Please, check your privileges. " +
        "Result: " +result2)

class DTraceTestsNormal(unittest.TestCase) :
    def setUp(self) :
        self.optimize = False

    def test_function_entry_return(self) :
        dscript = """
python$target:::function-entry
/(copyinstr(arg0)=="%(path)s") &&
(copyinstr(arg1)=="test_entry_return_and_stack")/
{
    self->trace = 1;
}
python$target:::function-entry,python$target:::function-return
/(copyinstr(arg0)=="%(path)s") && (self->trace)/
{
    printf("%%d\t**%%s*%%s*%%s*%%d\\n", timestamp,
        probename, copyinstr(arg0),
        copyinstr(arg1), arg2);
}
python$target:::function-return
/(copyinstr(arg0)=="%(path)s") &&
(copyinstr(arg1)=="test_entry_return_and_stack")/
{
    self->trace = 0;
}
""" %{"path":sample}

        dscript = dscript.replace("\r", "").replace("\n", "")
        expected_result = """
        **function-entry*%(path)s*test_entry_return_and_stack*25
        **function-entry*%(path)s*function_1*6
        **function-return*%(path)s*function_1*7
        **function-entry*%(path)s*function_2*10
        **function-entry*%(path)s*function_1*6
        **function-return*%(path)s*function_1*7
        **function-return*%(path)s*function_2*11
        **function-entry*%(path)s*function_3*14
        **function-return*%(path)s*function_3*15
        **function-entry*%(path)s*function_4*18
        **function-return*%(path)s*function_4*19
        **function-entry*%(path)s*function_5*22
        **function-return*%(path)s*function_5*23
        **function-return*%(path)s*test_entry_return_and_stack*30
        """ %{"path":sample}

        command = "%s %s" %(sys.executable, sample)
        if self.optimize :
            command = "%s -OO %s" %(sys.executable, sample)
        actual_result, _ = subprocess.Popen(["dtrace", "-q", "-n",
            dscript,
            "-c", command],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

        actual_result = normalize(actual_result)
        expected_result = expected_result.replace("\r", "").replace("\n",
                "").replace(" ", "")
        self.assertEqual(actual_result, expected_result)

    @unittest.skipIf(sys.platform == 'darwin',
        "MacOS X doesn't support jstack()")
    def test_stack(self) :
        dscript = """
python$target:::function-entry
/(copyinstr(arg0)=="%(path)s") &&
(copyinstr(arg1)=="test_entry_return_and_stack")/
{
    self->trace = 1;
}
python$target:::function-entry
/(copyinstr(arg0)=="%(path)s") && (self->trace)/
{
    printf("[x]");
    jstack();
}
python$target:::function-return
/(copyinstr(arg0)=="%(path)s") &&
(copyinstr(arg1)=="test_entry_return_and_stack")/
{
    self->trace = 0;
}
""" %{"path":sample}

        dscript = dscript.replace("\r", "").replace("\n", "")
        expected_result = """
        [x]
        [%(path)s:25(test_entry_return_and_stack)]
        [x]
        [%(path)s:6(function_1)]
        [%(path)s:26(test_entry_return_and_stack)]
        [x]
        [%(path)s:10(function_2)]
        [%(path)s:27(test_entry_return_and_stack)]
        [x]
        [%(path)s:6(function_1)]
        [%(path)s:11(function_2)]
        [%(path)s:27(test_entry_return_and_stack)]
        [x]
        [%(path)s:14(function_3)]
        [%(path)s:28(test_entry_return_and_stack)]
        [x]
        [%(path)s:18(function_4)]
        [%(path)s:29(test_entry_return_and_stack)]
        [x]
        [%(path)s:22(function_5)]
        [%(path)s:30(test_entry_return_and_stack)]
        """ %{"path":sample}

        command = "%s %s" %(sys.executable, sample)
        if self.optimize :
            command = "%s -OO %s" %(sys.executable, sample)
        actual_result, _ = subprocess.Popen(["dtrace", "-q", "-n",
            dscript,
            "-c", command],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

        # When compiling with '--with-pydebug'
        actual_result = "".join(re.split("\[[0-9]+ refs\]", actual_result))

        actual_result = [i for i in actual_result.split("\n") if (("[" in i)
            and not i.endswith(" (<module>) ]"))]
        actual_result = "".join(actual_result)
        actual_result = actual_result.replace("\r", "").replace("\n",
                "").replace(" ", "")
        expected_result = expected_result.replace("\r", "").replace("\n",
                "").replace(" ", "")
        self.assertEqual(actual_result, expected_result)

    def test_garbage_collection(self) :
        dscript = """
python$target:::gc-start,python$target:::gc-done
{
    printf("%d\t**%s(%ld)\\n", timestamp, probename, arg0);
}
"""

        dscript = dscript.replace("\r", "").replace("\n", "")
        command = "%s %s" %(sys.executable, sample)
        if self.optimize :
            command = "%s -OO %s" %(sys.executable, sample)
        actual_result, _ = subprocess.Popen(["dtrace", "-q", "-n",
            dscript,
            "-c", command],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

        actual_result = normalize(actual_result)
        for i in xrange(10) :
            actual_result = actual_result.replace(str(i), "")
        expected_result = "**gc-start()**gc-done()" * \
            actual_result.count("**gc-start()**")

        self.assertEqual(actual_result, expected_result)

    def test_verify_opcodes(self) :
        # Verify that we are checking:
        opcodes = set(["CALL_FUNCTION", "CALL_FUNCTION_VAR",
            "CALL_FUNCTION_KW", "CALL_FUNCTION_VAR_KW"])
        with open(sample) as f :
            obj = compile(f.read(), "sample", "exec")
        class dump() :
            def __init__(self) :
                self.buf = []
            def write(self, v) :
                self.buf.append(v)

        dump = dump()
        stdout = sys.stdout
        sys.stdout = dump
        for i in obj.co_consts :
            if isinstance(i, types.CodeType) and \
                (i.co_name == 'test_entry_return_and_stack') :
                dis.dis(i)
        sys.stdout = stdout
        dump = "\n".join(dump.buf)
        dump = dump.replace("\r", "").replace("\n", "").split()
        for i in dump :
            opcodes.discard(i)
        # Are we verifying all the relevant opcodes?
        self.assertEqual(set(), opcodes)  # Are we verifying all opcodes?

    def test_line(self) :
        dscript = """
python$target:::line
/(copyinstr(arg0)=="%(path)s") &&
(copyinstr(arg1)=="test_line")/
{
    printf("%%d\t**%%s*%%s*%%s*%%d\\n", timestamp,
        probename, copyinstr(arg0),
        copyinstr(arg1), arg2);
}
""" %{"path":sample}

        dscript = dscript.replace("\r", "").replace("\n", "")
        expected_result = """
        **line*%(path)s*test_line*33
        **line*%(path)s*test_line*34
        **line*%(path)s*test_line*35
        **line*%(path)s*test_line*36
        **line*%(path)s*test_line*37
        **line*%(path)s*test_line*38
        **line*%(path)s*test_line*34
        **line*%(path)s*test_line*35
        **line*%(path)s*test_line*36
        **line*%(path)s*test_line*37
        **line*%(path)s*test_line*38
        **line*%(path)s*test_line*34
        **line*%(path)s*test_line*39
        """ %{"path":sample}

        command = "%s %s" %(sys.executable, sample)
        if self.optimize :
            command = "%s -OO %s" %(sys.executable, sample)
        actual_result, _ = subprocess.Popen(["dtrace", "-q", "-n",
            dscript,
            "-c", command],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

        actual_result = normalize(actual_result)
        expected_result = expected_result.replace("\r", "").replace("\n",
                "").replace(" ", "")
        self.assertEqual(actual_result, expected_result)

    def test_instance_creation_destruction(self) :
        dscript = """
python$target:::function-entry
/(copyinstr(arg0)=="%(path)s") &&
(copyinstr(arg1)=="test_instance_creation_destruction")/
{
    self->trace = 1;
}

python$target:::instance-new-start,
python$target:::instance-new-done,
python$target:::instance-delete-start,
python$target:::instance-delete-done
/self->trace/
{
    printf("%%d\t**%%s* (%%s.%%s)\\n", timestamp,
        probename, copyinstr(arg1), copyinstr(arg0));
}

python$target:::function-return
/(copyinstr(arg0)=="%(path)s") &&
(copyinstr(arg1)=="test_instance_creation_destruction")/
{
    self->trace = 0;
}
""" %{"path":sample}

        dscript = dscript.replace("\r", "").replace("\n", "")
        expected_result = """
        **instance-new-start*(__main__.old_style_class)
        **instance-new-done*(__main__.old_style_class)
        **instance-delete-start*(__main__.old_style_class)
        **instance-delete-done*(__main__.old_style_class)
        **instance-new-start*(__main__.new_style_class)
        **instance-new-done*(__main__.new_style_class)
        **instance-delete-start*(__main__.new_style_class)
        **instance-delete-done*(__main__.new_style_class)
        **instance-new-start*(__main__.old_style_class)
        **instance-new-done*(__main__.old_style_class)
        **instance-new-start*(__main__.new_style_class)
        **instance-new-done*(__main__.new_style_class)
        **instance-delete-start*(__main__.old_style_class)
        **instance-delete-done*(__main__.old_style_class)
        **instance-delete-start*(__main__.new_style_class)
        **instance-delete-done*(__main__.new_style_class)
        """

        command = "%s %s" %(sys.executable, sample)
        if self.optimize :
            command = "%s -OO %s" %(sys.executable, sample)
        actual_result, _ = subprocess.Popen(["dtrace", "-q", "-n",
            dscript,
            "-c", command],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

        actual_result = normalize(actual_result)
        expected_result = expected_result.replace("\r", "").replace("\n",
                "").replace(" ", "")
        self.assertEqual(actual_result, expected_result)



# This class try to verify that dtrace probes
# are still working with optimizations enabled in the bytecode.
#
# Some tests will not actually verify it. For instance,
# source code compilation follows optimization status of
# current working Python. So, you should run the test
# both with an optimizing and a non optimizing Python.
class DTraceTestsOptimize(DTraceTestsNormal) :
    def setUp(self) :
        self.optimize = True


def test_main():
    run_unittest(DTraceTestsNormal)
    run_unittest(DTraceTestsOptimize)

if __name__ == '__main__':
    test_main()

