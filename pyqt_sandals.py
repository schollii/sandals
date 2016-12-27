# This file is part of the sandals suite of components, hosted on
# https://github.com/schollii/sandals.
#
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
#
# Use, distribution and modification of this file is bound by the terms
# of the MIT (expat) license.
#
# Copyright (c) Oliver Schoenborn

"""
Various utilities for PyQt-based components.
"""

from typing import Union

from PyQt5.QtCore import QMetaMethod, pyqtSlot, pyqtSignal, QObject, Qt


def check_has_signal(obj: QObject, signal: Union[pyqtSignal, str]):
    """
    Check that given object has given signal.

    :param obj: object on which to check for existence of Qt signal
    :param signal: a signal (return value from pyqtSignal(...)) or string of a signal name

    :raises: RuntimeError if it does not have the signal
    :raises: Attribute error if signal is a string and there is no such attribute on obj
    """
    if isinstance(signal, str):
        signal = getattr(obj, signal)

    meta = obj.metaObject()
    for i in range(0, meta.methodCount()):
        meta_meth = meta.method(i)
        if meta_meth.methodType() == QMetaMethod.Signal:
            meth_name = bytes(meta_meth.name()).decode()
            sig_meta = getattr(obj, meth_name)
            if sig_meta.signal == signal.signal:
                return

    raise RuntimeError("Object of type {} does not have a signal {}")


def is_connected(signal: pyqtSignal, slot: pyqtSlot) -> bool:
    """
    Determine if a (bound) signal is connected to a slot.
    :param signal: signal (a return value from a call to pyqtSignal(...))
    :param slot: slot (a method on a QObject, decorated with pyqtSlot)
    :return: True if connected, False otherwise
    """
    try:
        signal.connect(slot, Qt.UniqueConnection)

    except TypeError as exc:
        assert str(exc) in ('connection is not unique', 'connect() failed between MyObj.sig_test[] and meth()')
        return True

    else:
        signal.disconnect(slot)
        return False


def is_connected_obj(obj: QObject, signal: pyqtSignal, slot: pyqtSlot) -> bool:
    """
    Same as is_connected() but additionally checks that the signal belongs to an object
    :param obj: same as isthe object that has the signal is given, the function can assert that
    :param signal: signal (a return value from a call to pyqtSignal(...), on obj)
    :param slot: slot (a method on a QObject, decorated with pyqtSlot)
    :return: True if connected, False otherwise
    """
    num_recv = obj.receivers(signal)
    try:
        return is_connected(signal, slot)
    finally:
        assert obj.receivers(signal) == num_recv
