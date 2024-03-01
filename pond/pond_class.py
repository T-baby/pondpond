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
import asyncio
import math
import time
from asyncio import AbstractEventLoop
from collections import deque
from threading import RLock, Thread
from typing import TYPE_CHECKING, Any, Coroutine, Deque, Dict, Final, Optional

from .count_min_sketch import CountMinSketch
from .pooled_object import PooledObject
from .pooled_object_factory import PooledObjectFactory


class Pond(object):
    def __init__(
        self,
        borrowed_timeout: int = 60,
        time_between_eviction_runs: int = 300,
        eviction_weight: float = 0.8,
        thread_daemon: bool = True,
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        """Pond is a high performance object-pooling library for Python, it has
            a smaller memory usage and a higher hit rate.For more details,
            see our user's guide or my blog(https://qin.news).

        Args:
            borrowed_timeout (int, optional): The maximum duration of the
                borrowed object. Defaults to 60.
            time_between_eviction_runs (int, optional): The interval for
                automatic recycling. Defaults to 300. If its value is -1,
                the recycling is turned off.
            eviction_weight (float, optional): Automatic recycling weight.
                Defaults to 0.8.
            thread_daemon (bool, optional): A boolean value indicating whether
                the pond's thread is a daemon thread. Defaults to True.
        """
        self.__borrowed_timeout: int = borrowed_timeout
        if loop is not None:
            self.__loop = loop
        else:
            self.__loop = asyncio.new_event_loop()
        self.__time_between_eviction_runs = time_between_eviction_runs
        self.__eviction_weight = eviction_weight
        self.__async_lock = asyncio.Lock()
        self.__sync_lock = RLock()
        self.__class_dict: Final[Dict[str, PooledObjectFactory]] = dict()

        if TYPE_CHECKING:
            self.__pooled_object_tree: Final[Dict[str, Deque[PooledObject]]] = dict()
        else:
            self.__pooled_object_tree: Final[Dict[str, Deque]] = dict()
        self.counter: CountMinSketch = CountMinSketch(28, 3)

        def loop_runner(
            loop: AbstractEventLoop, function: Coroutine[Any, Any, None]
        ) -> None:
            asyncio.set_event_loop(loop)
            loop.create_task(function)
            loop.run_forever()

        if self.__time_between_eviction_runs > -1:
            self.__thread = Thread(
                target=loop_runner, args=(self.__loop, self.__eviction())
            )
            self.__thread.daemon = thread_daemon
            self.__thread.start()

    def register(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> None:
        """Registering the factory object with Pond will use the class name of
            the factory as the key for the PooledObjectTree by default.After
            successful registration, Pond will automatically start creating
            objects based on the pooled_maxsize set in factory until the pool
            is filled.

        Args:
            factory (Optional[PooledObjectFactory], optional): The factory
                object you want to register. Defaults to None.
            name (Optional[str], optional): The factory name you want to register.
                Defaults to None.

        Raises:
            ValueError: The factoryClass existed in the PooledObjectTree!
            ValueError: The instance must not be null!
        """
        if name is None:
            assert factory is not None
            name = factory.factory_name()
        assert factory is not None
        if self.__pooled_object_tree.__contains__(name):
            raise ValueError("The factoryClass existed in the PooledObjectTree!")
        self.__class_dict[name] = factory
        self.__pooled_object_tree[name] = deque(maxlen=factory.pooled_maxsize)
        for i in range(factory.pooled_maxsize):
            instance = self.__class_dict[name].createInstance()
            if instance is None:
                raise ValueError("The instance must not be null!")
            self.__pooled_object_tree[name].appendleft(instance)

    def borrow(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> PooledObject:
        """You can use factory object or factory name to borrow and return
            objects from the object pool.

        Args:
            factory (Optional[PooledObjectFactory], optional): The factory
                object you want to register. Defaults to None.
            name (Optional[str], optional): The factory name you want to register.
                Defaults to None.

        Returns:
            PooledObject: The pooled object you want to borrow.
        """
        with self.__sync_lock:
            if not name:
                assert factory is not None
                name = factory.factory_name()
            if self.is_empty(name=name):
                if self.__time_between_eviction_runs > -1:
                    self.counter.add(name)
                return self.__class_dict[name].createInstance()
            pooled_object = self.__pooled_object_tree[name].pop()
            while not self.__class_dict[name].validate(pooled_object):
                self.__clear_one_object(pooled_object, name=name)
                if self.is_empty(name=name):
                    pooled_object = self.__class_dict[name].createInstance()
                else:
                    pooled_object = self.__pooled_object_tree[name].pop()
            if self.__time_between_eviction_runs > -1:
                self.counter.add(name)
            return pooled_object.update_brrow_time()

    def recycle(
        self,
        pooled_object: PooledObject,
        factory: Optional[PooledObjectFactory] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """You can use factory object or factory name to borrow and return
            objects from the object pool.

        Args:
            pooled_object (PooledObject): The pooled object you want to recycle.
            factory (Optional[PooledObjectFactory], optional): The factory
                object you want to register. Defaults to None.
            name (Optional[str], optional): The factory name you want to register.
                Defaults to None.
            kwargs (Any): The parameters you want to pass to the reset method.
        """
        with self.__sync_lock:
            if not name:
                assert factory is not None
                name = factory.factory_name()
            if not isinstance(pooled_object, PooledObject):
                raise ValueError("Only PooledObject can be recycled!")
            if self.is_full(name=name):
                self.__clear_one_object(pooled_object, name=name)
                return
            if (time.time() - pooled_object.last_borrow_time) > self.__borrowed_timeout:
                self.__clear_one_object(pooled_object, name=name)
                return

            self.__pooled_object_tree[name].append(
                self.__class_dict[name].reset(pooled_object, **kwargs)
            )

    def clear(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> None:
        """You can use factory object or factory name to clear the object pool.

        Args:
            factory (Optional[PooledObjectFactory], optional): The factory
                object you want to register. Defaults to None.
            name (Optional[str], optional): The factory name you want to register.
                Defaults to None.
        """
        if not name:
            assert factory is not None
            name = factory.factory_name()
        while not self.is_empty(name=name):
            pooled_object = self.__pooled_object_tree[name].pop()
            self.__clear_one_object(pooled_object, name=name)

    def __clear_one_object(
        self,
        pooled_object: PooledObject,
        factory: Optional[PooledObjectFactory] = None,
        name: Optional[str] = None,
    ) -> None:
        if not name:
            assert factory is not None
            name = factory.factory_name()
        self.__class_dict[name].destroy(pooled_object)
        del pooled_object

    def size(self) -> int:
        """Query how many object pools there are in pooled_object_tree."""
        return len(self.__pooled_object_tree)

    def count_total_objects(self) -> int:
        """Query how many objects there are in pooled_object_tree."""
        total_number = 0
        for k, v in self.__pooled_object_tree.items():
            total_number = total_number + len(v)
        return total_number

    def contains(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> bool:
        """Return true if the specified factory has been registered in the pond.

        Args:
            factory (Optional[PooledObjectFactory], optional): The specified factory object. Defaults to None.
            name (Optional[str], optional): The specified factory name. Defaults to None.

        Returns:
            bool: Return true if the specified factory has been registered in the pond.
        """
        if name is None:
            assert factory is not None
            name = factory.factory_name()
        return self.__pooled_object_tree.__contains__(name)

    def pooled_object_size(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> int:
        """Query how many objects there are in the specified object pool.

        Args:
            factory (Optional[PooledObjectFactory], optional): The specified factory object. Defaults to None.
            name (Optional[str], optional): The specified factory name. Defaults to None.

        Returns:
            int: Size of the specified object pool.
        """
        if not name:
            assert factory is not None
            name = factory.factory_name()
        return len(self.__pooled_object_tree[name])

    def is_full(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> bool:
        """Check to see if the supplied object pool is filled.

        Args:
            factory (Optional[PooledObjectFactory], optional): The specified factory object. Defaults to None.
            name (Optional[str], optional): The specified factory name. Defaults to None.

        Returns:
            bool: Whether the object pool is full.
        """
        if not name:
            assert factory is not None
            name = factory.factory_name()
        return len(self.__pooled_object_tree[name]) >= (
            self.__pooled_object_tree[name].maxlen or 0
        )

    def is_empty(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> bool:
        """Check to see if the supplied object pool is emptied.

        Args:
            factory (Optional[PooledObjectFactory], optional): The specified factory object. Defaults to None.
            name (Optional[str], optional): The specified factory name. Defaults to None.

        Returns:
            bool: Whether the object pool is empty.
        """
        if not name:
            assert factory is not None
            name = factory.factory_name()
        return len(self.__pooled_object_tree[name]) == 0

    def __reset_counter(self) -> None:
        n = self.size()
        if n == 0:
            epsilon = 0.1
        else:
            epsilon = 10 / n
        if epsilon >= 1:
            epsilon = 0.1
        m = math.ceil(math.e / epsilon)
        d = math.ceil(math.log(1 / 0.1))
        if not m == self.counter.m or not d == self.counter.d:
            self.counter = CountMinSketch(m, d)

    def stop(self) -> None:
        """Stop the pone and all objects in the pooled object tree will be destroyed."""
        self.__loop.stop()
        self.__time_between_eviction_runs = -1
        for key in self.__pooled_object_tree.keys():
            self.clear(name=key)

    async def __eviction(self, debug: bool = False) -> None:
        first_run = True
        while self.__time_between_eviction_runs > 0:
            if first_run:
                first_run = False
                await asyncio.sleep(self.__time_between_eviction_runs)
                continue
            pooled_object_borrow_count: Dict[str, int] = {}
            max_count = 8
            for key in self.__pooled_object_tree.keys():
                pooled_object_borrow_count[key] = self.counter[key]
            boundary = int(max_count * self.__eviction_weight)
            for key, value in pooled_object_borrow_count.items():
                size = len(self.__pooled_object_tree[key])
                if value < boundary and size > 0:
                    if size > 1:
                        for i in range(int(size / 2)):
                            self.__clear_one_object(
                                self.__pooled_object_tree[key].pop(),
                                name=key,
                            )
                    else:
                        if not self.__class_dict[key].least_one:
                            self.clear(name=key)
            self.__reset_counter()
            if debug:
                self.__time_between_eviction_runs = -1
            await asyncio.sleep(self.__time_between_eviction_runs)

    async def async_register(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> None:
        async with self.__async_lock:
            self.register(factory=factory, name=name)

    async def async_borrow(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> PooledObject:
        async with self.__async_lock:
            return self.borrow(factory=factory, name=name)

    async def async_recycle(
        self,
        pooled_object: PooledObject,
        factory: Optional[PooledObjectFactory] = None,
        name: Optional[str] = None,
    ) -> None:
        async with self.__async_lock:
            self.recycle(pooled_object=pooled_object, factory=factory, name=name)

    async def async_clear(
        self, factory: Optional[PooledObjectFactory] = None, name: Optional[str] = None
    ) -> None:
        async with self.__async_lock:
            self.clear(factory=factory, name=name)
