# sandals
Various pieces of code for various tasks :)

## PyQt 5 signal/slot connections performance

The PyQt5 website indicates that using `@pyqtSlot(...)` decreases the amount
of memory required and increases speed, although the site is not clear in what way. I wrote 
pyqt5_connections_mem_speed.py to get specifics on this statement. 

Results are discussed in a [CodeProject article](http://www.codeproject.com/Articles/1123088/PyQt-signal-slot-connection-performance)
