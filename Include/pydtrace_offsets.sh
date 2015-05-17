#!/bin/sh

DTRACE_NM=$1
CEVAL_O=$2
PYDTRACE_OFFSETS=$3
if test "$DTRACE_NM" = "OTHER" ; then
    $PYDTRACE_OFFSETS \
		"`nm -n $CEVAL_O | grep \" T \" | \
		sed -n \"/ T PyEval_EvalFrameEx$/{n;p;}\" | \
		sed \"s/.* T \(.*\)$/\1/\"`" \
		"`nm -n $CEVAL_O | grep \" T \" | \
		sed -n \"/ T PyEval_EvalFrameExReal$/{n;p;}\" | \
		sed \"s/.* T \(.*\)$/\1/\"`"
fi
if test "$DTRACE_NM" = "SOLARIS" ; then 
    $PYDTRACE_OFFSETS \
		"`/usr/ccs/bin/nm -n $CEVAL_O | \
		/usr/bin/grep \"\\|FUNC \\|\" | \
		/usr/bin/grep -v \"\\|IGNORE \\|\" | \
		/usr/bin/tr -d \"\\[\\]\\|\" | sort -n | \
		sed -n \"/ PyEval_EvalFrameEx$/{n;p;}\" | \
		sed \"s/.* \([a-zA-Z0-9_]*\)$/\1/\"`" \
		"`/usr/ccs/bin/nm -n $CEVAL_O | \
		/usr/bin/grep \"\\|FUNC \\|\" | \
		/usr/bin/grep -v \"\\|IGNORE \\|\" | \
	       	/usr/bin/tr -d \"\\[\\]\\|\" | sort -n | \
		sed -n \"/ PyEval_EvalFrameExReal$/{n;p;}\" | \
		sed \"s/.* \([a-zA-Z0-9_]*\)$/\1/\"`"
fi

