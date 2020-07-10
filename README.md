# sandals
Various pieces of code for various tasks :)

## JSON data structure semantically invariant hash

When you need to compare two JSON data structures without caring about order of dictionary keys, 
or just get a hash that will not change as long as the data structure doesn't semantically vary, 
check out the json_sem_hash.py module. 

## PyQt 5 signal/slot connections performance

The PyQt5 website indicates that using `@pyqtSlot(...)` decreases the amount
of memory required and increases speed, although the site is not clear in what way. I wrote 
pyqt5_connections_mem_speed.py to get specifics on this statement. 

Results are discussed in a [CodeProject article](http://www.codeproject.com/Articles/1123088/PyQt-signal-slot-connection-performance)

## PyQt Widget snapshot checker

Utility components to check whether a widget looks identical or similar within tolerance to an existing snapshot of it. 
Discussed in [CodeProject article](http://www.codeproject.com/Tips/1134902/Testing-QWidget-Snapshot-Regression-in-PyQt).
