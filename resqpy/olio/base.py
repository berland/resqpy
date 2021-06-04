"""Base class for generic resqml objects """

from abc import ABCMeta, abstractmethod
from typing import Iterable

import resqpy.olio.uuid as bu
import resqpy.olio.write_hdf5 as rwh5
from resqpy.olio.attributes import BaseAttribute, HdfAttribute


class BaseResqml(metaclass=ABCMeta):
    """Base class for generic RESQML objects"""

    _attrs: Iterable[BaseAttribute] = ()

    def __init__(self, model, uuid=None, title=None, originator=None):
        self.model = model
        self.title = title
        self.originator = originator

        self._root = None  # Root in memory, may not be in model

        if uuid is None:
            self.uuid = bu.new_uuid()
        else:
            self.uuid = uuid
            self.load_from_xml()

    @property
    @abstractmethod
    def _resqml_obj(self):
        # Must be overridden in child classes
        raise NotImplementedError

    @property
    def root(self):
        """Node corresponding to self.uuid"""

        if self.uuid is None:
            raise ValueError('Cannot get root if uuid is None')
        if self._root is not None:
            return self._root
        return self.model.root_for_uuid(self.uuid)

    @root.setter
    def root(self, value):
        self._root = value

    @property
    def part(self):
        """Part corresponding to self.uuid"""
        if self.uuid is None:
            raise ValueError('Cannot get part if uuid is None')
        return self.model.part_for_uuid(self.uuid)
    
    def load_from_xml(self):
        """Load attributes from XML and HDF5"""

        for attr in self._attrs:
            attr.load(self)

    def create_xml(self, title=None, originator=None, ext_uuid=None):
        """Write XML for object
        
        Args:
            title (string): used as the citation Title text; should usually refer to the well name in a
                human readable way
            originator (string, optional): the name of the human being who created the deviation survey part;
                default is to use the login name
        
        """

        assert self.uuid is not None

        if ext_uuid is None: ext_uuid = self.model.h5_uuid()

        node = self.model.new_obj_node(self._resqml_obj)
        node.attrib['uuid'] = str(self.uuid)
        self.root = node

        assert self.root is not None

        # Citation block
        if title: self.title = title
        if originator: self.originator = originator
        self.model.create_citation(
            root=node, title=self.title, originator=self.originator
        )

        # XML and HDF5 attributes
        for attr in self._attrs:
            attr.write_xml(obj=self)

    def write_hdf5(self, file_name=None, mode='a'):
        """Create or append to an hdf5 file"""

        hdf_attrs = [a for a in self._attrs if isinstance(a, HdfAttribute)]

        if len(hdf_attrs) == 0:
            raise ValueError(f"Class {self} has no HDF5 attributes to write")
        
        h5_reg = rwh5.H5Register(self.model)
        for attr in hdf_attrs:
            array = getattr(self, attr.key)
            h5_reg.register_dataset(self.uuid, attr.tag, array, dtype=attr.dtype)
        h5_reg.write(file=file_name, mode=mode)
