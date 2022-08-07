"""
From https://github.com/rafacarrascosa/countminsketch/
----
Copyright (c) 2014, Rafael Carrascosa
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the Rafael Carrascosa nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL RAFAEL CARRASCOSA BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import hashlib
import array
import math


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

    def __init__(self, m, d):
        """ `m` is the size of the hash tables, larger implies smaller
        overestimation. `d` the amount of hash tables, larger implies lower
        probability of overestimation.
        """
        if not m or not d:
            raise ValueError("Table size (m) and amount of hash functions (d)"
                             " must be non-zero")
        self.m = m
        self.d = d
        self.n = 0
        self.tables = []
        for _ in range(d):
            table = array.array("l", (0 for _ in range(m)))
            self.tables.append(table)

    def _hash(self, x):
        md5 = hashlib.md5(str(hash(x)).encode("utf-8"))
        for i in range(self.d):
            md5.update(str(i).encode("utf-8"))
            yield int(md5.hexdigest(), 16) % self.m

    def add(self, x, value=1):
        """
        Count element `x` as if had appeared `value` times.
        By default `value=1` so:
            sketch.add(x)
        Effectively counts `x` as occurring once.
        """
        if isinstance(x, str):
            x = x.encode("utf-8")
        self.n += value
        for table, i in zip(self.tables, self._hash(x)):
            table[i] += value
            if table[i] >= 8:
                for table in self.tables:
                    for i,v in enumerate(table):
                        table[i] = math.ceil(v/2)

    def query(self, x):
        """
        Return an estimation of the amount of times `x` has ocurred.
        The returned value always overestimates the real value.
        """
        return min(table[i] for table, i in zip(self.tables, self._hash(x)))

    def __getitem__(self, x):
        """
        A convenience method to call `query`.
        """
        return self.query(x)

    def __len__(self):
        """
        The amount of things counted. Takes into account that the `value`
        argument of `add` might be different from 1.
        """
        return self.n
