provider python {
    probe function__entry(const char *, const char *, int);
    probe function__return(const char *, const char *, int);
    probe instance__new__start(const char *, const char *);
    probe instance__new__done(const char *, const char *);
    probe instance__delete__start(const char *, const char *);
    probe instance__delete__done(const char *, const char *);
    probe line(const char *, const char *, int);
    probe gc__start(int);
    probe gc__done(long);
};

#pragma D attributes Evolving/Evolving/Common provider python provider
#pragma D attributes Private/Private/Common provider python module
#pragma D attributes Private/Private/Common provider python function
#pragma D attributes Evolving/Evolving/Common provider python name
#pragma D attributes Evolving/Evolving/Common provider python args



#ifdef PYDTRACE_STACK_HELPER
/*
 * Python ustack helper.  This relies on the first argument (PyFrame *) being
 * on the stack; see Python/ceval.c for the contortions we go through to ensure
 * this is the case.
 *
 * On x86, the PyFrame * is two slots up from the frame pointer; on SPARC, it's
 * eight.
 *
 * Some details about this in "Python and DTrace in build 65":
 * http://blogs.oracle.com/levon/entry/python_and_dtrace_in_build
 */

/*
 * Yes, this is as gross as it looks. DTrace cannot handle static functions,
 * and our stat_impl.h has them in ILP32.
 */
#define _SYS_STAT_H

/*
** When compiling in 32 bits:
** - Early inclusion to avoid problems with
**   _FILE_OFFSET_BITS redefined.
** - Also, we must "undef" _POSIX_PTHREAD_SEMANTICS
**   to avoid error compiling this source.
*/
#include "pyconfig.h"
#undef _POSIX_PTHREAD_SEMANTICS

#include <stdio.h>
#include <sys/types.h>

#include "pyport.h"
#include "object.h"
#include "pystate.h"
#include "pyarena.h"
#include "pythonrun.h"
#include "compile.h"
#include "frameobject.h"
#include "stringobject.h"

#include "pydtrace_offsets.h"

#if defined(__i386)
#define	startframe PyEval_EvalFrameEx
#define	endframe AFTER_PyEval_EvalFrameEx
#elif defined(__amd64)
#define	startframe PyEval_EvalFrameExReal
#define	endframe AFTER_PyEval_EvalFrameExReal
#elif defined(__sparc)
#define	startframe PyEval_EvalFrameExReal
#define	endframe AFTER_PyEval_EvalFrameExReal
#endif

#ifdef __sparcv9
#define	STACK_BIAS (2048-1)
#else
#define	STACK_BIAS 0
#endif

#define	at_evalframe(addr) \
    ((uintptr_t)addr >= ((uintptr_t)&``startframe) && \
     (uintptr_t)addr < ((uintptr_t)&``endframe))
#define	probe dtrace:helper:ustack:
#define	print_result(r) (r)

#if defined(__i386) || defined(__amd64)
#define	frame_ptr_addr ((uintptr_t)arg1 + sizeof(uintptr_t) * 2)
#elif defined(__sparc)
#define	frame_ptr_addr ((uintptr_t)arg1 + STACK_BIAS + sizeof(uintptr_t) * 8)
#else
#error unknown architecture
#endif

/* startframe and endframe are macro-expansions */
extern uintptr_t startframe;
extern uintptr_t endframe;

#define	copyin_obj(addr, obj) ((obj *)copyin((uintptr_t)(addr), sizeof(obj)))
#define	pystr_addr(addr) ((char *)addr + offsetof(PyStringObject, ob_sval))
#define	copyin_str(dest, addr, obj) \
    (copyinto((uintptr_t)pystr_addr(addr), obj->ob_size, (dest)))
#define	add_str(addr, obj) \
    copyin_str(this->result + this->pos, addr, obj); \
    this->pos += obj->ob_size; \
    this->result[this->pos] = '\0';
#define	add_digit(nr, div) ((nr / div) ? \
    (this->result[this->pos++] = '0' + ((nr / div) % 10)) : \
    (this->result[this->pos] = '\0'))
#define	add_char(c) (this->result[this->pos++] = c)

probe /at_evalframe(arg0)/ 
{
	this->framep = *(uintptr_t *)copyin(frame_ptr_addr, sizeof(uintptr_t));
	this->frameo = copyin_obj(this->framep, PyFrameObject);
	this->codep = this->frameo->f_code;
	this->codeo = copyin_obj(this->codep, PyCodeObject);
	/* If we just enter a function, show the definition line */
	this->lineno = this->codeo->co_firstlineno +
		(this->frameo->f_lasti == -1 ? 0 :
		*copyin_obj(this->codeo->co_linenos + this->frameo->f_lasti,
				unsigned short));
	this->filenamep = this->codeo->co_filename;
	this->fnamep = this->codeo->co_name;
	this->filenameo = copyin_obj(this->filenamep, PyStringObject);
	this->fnameo = copyin_obj(this->fnamep, PyStringObject);

	this->len = 1 + this->filenameo->ob_size + 1 + 5 + 2 +
	    this->fnameo->ob_size + 1 + 1;

	this->result = (char *)alloca(this->len);
	this->pos = 0;

	add_char('@');
	add_str(this->filenamep, this->filenameo);
	add_char(':');
	add_digit(this->lineno, 10000);
	add_digit(this->lineno, 1000);
	add_digit(this->lineno, 100);
	add_digit(this->lineno, 10);
	add_digit(this->lineno, 1);
	add_char(' ');
	add_char('(');
	add_str(this->fnamep, this->fnameo);
	add_char(')');
	this->result[this->pos] = '\0';

	print_result(stringof(this->result));
}

probe /!at_evalframe(arg0)/
{
	NULL;
}

#endif  /* PYDTRACE_STACK_HELPER */

