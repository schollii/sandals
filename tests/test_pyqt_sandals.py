import pytest
from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal

from pyqt_sandals import is_connected, is_connected_obj, check_has_signal


class TestSignalling:
    def test_connected_basic(self):
        class MyObj(QObject):
            sig_test = pyqtSignal()

        class Listener(QObject):
            @pyqtSlot()
            def meth(self):
                pass

        obj = MyObj()
        obs = Listener()

        assert obj.receivers(obj.sig_test) == 0
        obj.sig_test.connect(obs.meth, Qt.UniqueConnection)
        assert obj.receivers(obj.sig_test) == 1
        obj.sig_test.disconnect(obs.meth)
        assert obj.receivers(obj.sig_test) == 0

        # second time:
        obj.sig_test.connect(obs.meth, Qt.UniqueConnection)
        assert obj.receivers(obj.sig_test) == 1
        obj.sig_test.disconnect(obs.meth)
        assert obj.receivers(obj.sig_test) == 0

    def test_connected(self):
        class MyObj(QObject):
            sig_test = pyqtSignal()

        class Listener(QObject):
            @pyqtSlot()
            def meth(self):
                pass

        obj = MyObj()
        obs = Listener()
        assert not is_connected_obj(obj, obj.sig_test, obs.meth)
        assert not is_connected_obj(obj, obj.sig_test, obs.meth)
        assert not is_connected(obj.sig_test, obs.meth)
        assert not is_connected(obj.sig_test, obs.meth)

        obj.sig_test.connect(obs.meth)
        assert is_connected_obj(obj, obj.sig_test, obs.meth)
        assert is_connected(obj.sig_test, obs.meth)

    def test_check_signal(self):
        class MyObj(QObject):
            sig_test = pyqtSignal()

        class MyObj2(QObject):
            sig_test2 = pyqtSignal()

        obj = MyObj()
        obj2 = MyObj2()

        check_has_signal(obj, 'sig_test')
        check_has_signal(obj, obj.sig_test)

        check_has_signal(obj2, 'sig_test2')
        check_has_signal(obj2, obj2.sig_test2)

        pytest.raises(RuntimeError, check_has_signal, obj, obj2.sig_test2)
        pytest.raises(RuntimeError, check_has_signal, obj2, obj.sig_test)
        pytest.raises(AttributeError, check_has_signal, obj, 'sig_test2')
        pytest.raises(AttributeError, check_has_signal, obj2, 'sig_test')
