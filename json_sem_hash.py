"""
Compute a hash for a JSON data structure, such that semantically equivalent 
JSON structures get the same hash. The notion of "semantic equivalence" is 
currently rather basic and informal. Eg, the following are semantically 
equivalent, and this is reflected in the computed hashes: 
```
d3 = {'d1': {'a': 1, 'b': [1,2]}, 'd2': {'b': [1,2], 'a': 1}, 'L': [1, 2, 3]}
d4 = {'d2': {'b': [1,2], 'a': 1}, 'L': [1, 2, 3], 'd1': {'a': 1, 'b': [1,2]}}
print('d3 hash:', get_json_sem_hash(d3))
print('d4 hash:', get_json_sem_hash(d4))
assert get_json_sem_hash(d3) == get_json_sem_hash(d4)
```
This prints hash value 'e17246aa9136a25581fb859fdeb2dd1da4cda9a221124cd27208646749b85cd7'
for both d3 and d4. 

If you find that `get_json_sem_hash()` doesn't return the same hash for 2 json structures 
that *you* think are in fact "semantically equivalent", please raise an issue!

(C) Oliver Schoenborn
License: modified MIT, ie MIT plus the following restriction: This code can be 
included in your code base as the complete file only. 
"""

from pathlib import Path
from typing import Union, Dict, List, Any
import json

JsonType = Union[str, int, float, List['JsonType'], 'JsonTree']
JsonTree = Dict[str, JsonType]
StrTreeType = Union[str, List['StrTreeType'], 'StrTree']
StrTree = Dict[str, StrTreeType]


def sorted_dict_str(data: JsonType) -> StrTreeType:
    if type(data) == dict:
        return {k: sorted_dict_str(data[k]) for k in sorted(data.keys())}
    elif type(data) == list:
        return [sorted_dict_str(val) for val in data]
    else:
        return str(data)


def get_json_sem_hash(data: JsonTree, hasher=hashlib.sha256) -> str:
    return hasher(bytes(repr(sorted_dict_str(data)), 'UTF-8')).hexdigest()
