"""
Test the memory and cpu time consumption of signal/slot connections in PyQt5. Run this from a command
shell, have a coffee and see the results.

Dependencies:

- PyQt 5.x (pip install pyqt5)
- psutil (pip install psutil)
- Python 3.4 or later (although easily adapted for 2.7+ versions: replace statistics.* and time.perf_counter)

Tested only on Windows 7 but should work on any platform that supports standard CPython.
"""

import os
import gc
import psutil
from time import perf_counter
from statistics import mean, stdev

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, Qt, QCoreApplication, pyqtSlot

app = QCoreApplication([])

NUM_SAMPLES = 1000
NUM_EMITS_PER_SAMPLE = 1000000  # SLOW (30 minutes on my laptop`s virtual machine)
# NUM_EMITS_PER_SAMPLE = 10000
WRAP_SLOT = False


def slot_wrapper(func):
    def wrapped_slot():
        func()

    pyqt_slot = pyqtSlot()(wrapped_slot)
    assert pyqt_slot is wrapped_slot
    return pyqt_slot


def measure_speed(slot_type_raw: bool) -> float:
    class Emitter(QObject):
        sig_speed = pyqtSignal()

        def emit(self):
            start = perf_counter()
            for i in range(NUM_EMITS_PER_SAMPLE):
                self.sig_speed.emit()
            self.exec_time = perf_counter() - start
            app.exit()

    if slot_type_raw:
        class Handler:
            def slot(self):
                pass
    else:
        class Handler(QObject):
            # @pyqtSlot()
            def slot(self):
                pass

            wrapped_slot = slot_wrapper(slot)

    emitter = Emitter()
    handler = Handler()
    emitter.sig_speed.connect(handler.slot)
    QTimer.singleShot(0, emitter.emit)

    app.exec()
    return emitter.exec_time


def sample_speeds(slot_type_raw: bool) -> [float]:
    avg_times = []
    for i in range(NUM_SAMPLES):
        sample_time = measure_speed(slot_type_raw=True)
        avg_times.append(sample_time)
        if i == 10:
            expect_time = round(mean(avg_times) * NUM_SAMPLES)
            print('({}: expect approx {} sec more to complete)'.format('Raw' if slot_type_raw else 'Pyqt Slot',
                                                                       expect_time))

    return avg_times


def compare_speed():
    print('Comparing speed for {} samples of {} emits'.format(NUM_SAMPLES, NUM_EMITS_PER_SAMPLE))

    avg_times_raw = sample_speeds(True)
    mean_raw = mean(avg_times_raw)

    avg_times_pyqtslot = sample_speeds(False)
    mean_pyqtslot = mean(avg_times_pyqtslot)

    percent_gain = (mean_raw - mean_pyqtslot) / mean_pyqtslot * 100
    print('')
    print('Raw slot mean, stddev: ', round(mean_raw, 3), round(stdev(avg_times_raw), 3))
    print('Pyqt slot mean, stddev:', round(mean_pyqtslot, 3), round(stdev(avg_times_pyqtslot), 3))
    print('Percent gain with pyqtSlot:', round(percent_gain), '%')

    print('')
    print('Raw times:      ', [round(t, 3) for t in avg_times_raw])
    print('Pyqt slot times:', [round(t, 3) for t in avg_times_pyqtslot])
    print('')


def get_current_mem():
    process = psutil.Process(os.getpid())
    # return process.memory_info().rss
    return process.memory_full_info().uss


def measure_mem(num_connections: int, slot_type_raw: bool):
    gc.collect()

    class Emitter(QObject):
        sig_speed = pyqtSignal()

    if slot_type_raw:
        class Handler:
            def slot(self):
                pass

    else:
        class Handler(QObject):
            def slot(self):
                pass
            slot = pyqtSlot()(slot) if WRAP_SLOT else slot_wrapper(slot)

    emitter = Emitter()
    handlers = [Handler() for i in range(num_connections)]
    assert handlers[0] is not handlers[1]

    gc.collect()
    mem_start = get_current_mem()
    time_start = perf_counter()
    for handler in handlers:
        emitter.sig_speed.connect(handler.slot)
    time_used = perf_counter() - time_start
    mem_used = get_current_mem() - mem_start
    # assert mem_used != 0

    return mem_used, time_used


def compare_mem():
    MAX_POWER = 7
    print('Comparing mem and time required to create N connections, N from 100 to {}\n'.format(pow(10, MAX_POWER)))

    for power in range(2, MAX_POWER):
        num_connections = pow(10, power)
        print('Measuring for {} connections'.format(num_connections))
        print('{:12}  {:10} {:>15} {:>12}'.format('', '# connects', 'mem (bytes)', 'time (sec)'))

        mem_raw, time_raw = measure_mem(num_connections, slot_type_raw=True)
        mem_pyqtslot, time_pyqtslot = measure_mem(num_connections, slot_type_raw=False)

        print('{:12}: {:10} {:15} {:12.3}'.format('Raw', num_connections, mem_raw, time_raw))
        print('{:12}: {:10} {:15} {:12.3}'.format('Pyqt Slot', num_connections, mem_pyqtslot, time_pyqtslot))
        if mem_pyqtslot == 0:
            print('{:12}: {:10} {:>15} {:12}\n'.format('Ratios', '', 'nan',
                                                       round(time_raw / time_pyqtslot)))
        else:
            print('{:12}: {:10} {:15} {:12}\n'.format('Ratios', '',
                                                      round(mem_raw / mem_pyqtslot),
                                                      round(time_raw / time_pyqtslot)))


def compare_mem_time_stats(num_connections):
    print('Comparing mem and time required to create {} connections\n'.format(num_connections))

    print('{:12}  {:15} {:>15} {:>15} {:>15} {:>15}'.format(
        '', '# connects', 'avg mem (bytes)', 'uncert mem', 'avg time (sec)', 'uncert time'))
    raw_mems, raw_times = [], []
    pyqtslot_mems, pyqtslot_times = [], []
    for i in range(1000):
        mem_raw, time_raw = measure_mem(num_connections, slot_type_raw=True)
        mem_pyqtslot, time_pyqtslot = measure_mem(num_connections, slot_type_raw=False)
        raw_mems.append(mem_raw)
        raw_times.append(time_raw)
        pyqtslot_mems.append(mem_pyqtslot)
        pyqtslot_times.append(time_pyqtslot)

    def output_stats(label: str, mems, times):
        mean_mem = int(mean(mems))
        uncert_mem = int(stdev(mems))
        # print(mems)
        mean_time = mean(times)
        uncert_time = stdev(times)
        print('{:12}: {:15} {:15} {:15} {:15} {:15}'.format(
            label, num_connections, mean_mem, round(uncert_mem, 3), round(mean_time, 5), round(uncert_time, 3)))

        return mean_mem, mean_time

    mean_mem_raw, mean_time_raw = output_stats('Raw', raw_mems, raw_times)
    mean_mem_pyqt, mean_time_pyqt = output_stats('Pyqt Slot', pyqtslot_mems, pyqtslot_times)
    print('{:12}: {:15} {:15} {:15} {:15}\n'.format('Ratios',
                                                    '',
                                                    round(mean_mem_raw / mean_mem_pyqt),
                                                    '',
                                                    round(mean_time_raw / mean_time_pyqt)))


compare_speed()
compare_mem()
# compare_mem_time_stats(10)
# compare_mem_time_stats(100)
# compare_mem_time_stats(1000)
