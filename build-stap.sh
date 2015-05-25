#!/bin/bash
make clean
./configure --prefix=/opt/python --enable-ipv6 --enable-unicode=ucs4 --with-dbmliborder=bdb:gdbm --with-system-expat --with-system-ffi --with-fpectl CC=x86_64-linux-gnu-gcc CFLAGS="-D_FORTIFY_SOURCE=2 -g -fstack-protector --param=ssp-buffer-size=4 -Wformat -Werror=format-security" --with-dtrace
cp Modules/Setup.dist Modules/Setup
#make
