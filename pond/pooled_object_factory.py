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
import abc
from typing import Any

from .pooled_object import PooledObject


class PooledObjectFactory(metaclass=abc.ABCMeta):
    def __init__(self, pooled_maxsize: int = 8, least_one: bool = False) -> None:
        """Initialize the pooled object factory.

        Args:
            pooled_maxsize (int, optional): The maximum size of the pooled object. Defaults to 8.
            least_one (bool, optional): Whether to keep at least one pooled object. Defaults to False.
        """
        self.pooled_maxsize = pooled_maxsize
        self.least_one = least_one

    @abc.abstractmethod
    def createInstance(self) -> PooledObject:
        """Create a new pooled object.

        Returns:
            PooledObject: The new pooled object.
        """
        pass

    @abc.abstractmethod
    def destroy(self, pooled_object: PooledObject) -> None:
        """Destroy the pooled object.

        Args:
            pooled_object (PooledObject): The pooled object to be destroyed.
        """
        pass

    @abc.abstractmethod
    def reset(self, pooled_object: PooledObject, **kwargs: Any) -> PooledObject:
        """Reset the pooled object to the initial state.

        Args:
            pooled_object (PooledObject): The pooled object to be reset.
            **kwargs (Any): The arguments to be used to reset the pooled object.

        Returns:
            PooledObject: The reset pooled object.
        """
        pass

    @abc.abstractmethod
    def validate(self, pooled_object: PooledObject) -> bool:
        """Validate the pooled object.

        Args:
            pooled_object (PooledObject): The pooled object to be reset.

        Returns:
            bool: True if the pooled object is valid, otherwise False. If the pooled object is not valid,
            it will be destroyed.
        """
        pass

    def factory_name(self) -> str:
        return self.__class__.__qualname__
