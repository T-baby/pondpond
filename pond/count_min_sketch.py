"""
Copyright 2022 Andy Qin. All Rights Reserved.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import array
import hashlib
import math
import typing as t
from threading import RLock, Thread

import madoka


class CountMinSketch(object):
    """
    A class for counting hashable items using the Count-min Sketch strategy.
    It fulfills a similar purpose than `itertools.Counter`.
    The Count-min Sketch is a randomized data structure that uses a constant
    amount of memory and has constant insertion and lookup times at the cost
    of an arbitrarily small overestimation of the counts.
    It has two parameters:
     - `m` the size of the hash tables, larger implies smaller overestimation
     - `d` the amount of hash tables, larger implies lower probability of
           overestimation.
    An example usage:
        from countminsketch import CountMinSketch
        sketch = CountMinSketch(1000, 10)  # m=1000, d=10
        sketch.add("oh yeah")
        sketch.add(tuple())
        sketch.add(1, value=123)
        print sketch["oh yeah"]       # prints 1
        print sketch[tuple()]         # prints 1
        print sketch[1]               # prints 123
        print sketch["non-existent"]  # prints 0
    Note that this class can be used to count *any* hashable type, so it's
    possible to "count apples" and then "ask for oranges". Validation is up to
    the user.
    """

    def __init__(self, m: int, d: int):
        """`m` is the size of the hash tables, larger implies smaller
        overestimation. `d` the amount of hash tables, larger implies lower
        probability of overestimation.
        """
        if not m or not d:
            raise ValueError(
                "Table size (m) and amount of hash functions (d)" " must be non-zero"
            )
        self.m: int = m
        self.d: int = d
        self.sketch = madoka.Sketch(width=m, k=d, max_value=8)
        self.lock = False

    def add(self, x: t.Hashable) -> None:
        """
        Count element `x` as if had appeared `value` times.
        Effectively counts `x` as occurring once.
        """
        count = self.sketch[x]
        self.sketch[x] = count + 1
        if count >= 8:
            if not self.lock:
                self._clean()

    def _clean(self) -> None:
        self.sketch.filter(lambda x: math.floor(x / 2))

    def query(self, x: t.Hashable) -> int:
        """
        Return an estimation of the amount of times `x` has ocurred.
        The returned value always overestimates the real value.
        """
        return self.sketch.get(x)

    def __getitem__(self, x: t.Hashable) -> int:
        """
        A convenience method to call `query`.
        """
        return self.sketch.get(x)
