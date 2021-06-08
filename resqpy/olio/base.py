"""Base class for generic resqml objects """

import logging
import warnings
from abc import ABCMeta, abstractmethod
from typing import Iterable

import resqpy.olio.uuid as bu
import resqpy.olio.write_hdf5 as rwh5
import resqpy.olio.xml_et as rqet
from resqpy.olio.attributes import BaseAttribute, HdfAttribute


logger = logging.getLogger(__name__)


class BaseResqml(metaclass=ABCMeta):
    """Base class for generic RESQML objects"""

    # Subclasses can define simple XML or HDF attributes,
    # and the base class will handle loading and saving
    _attrs: Iterable[BaseAttribute] = ()

    # Subclasses must define which RESQML property they handle,
    # by overwriting the _resqml_obj attribute

    @property
    @abstractmethod
    def _resqml_obj(self):
        raise NotImplementedError

    def __init__(self, model, uuid=None, title=None, originator=None):
        """Load an existing resqml object, or create new.

        Args:
            model (resqpy.model.Model): Parent model
            uuid (str, optional): Load from existing uuid (if given), else create new.
            title (str, optional): Citation title
            originator (str, optional): Creator of object. By default, uses user id.
        """
        self.model = model
        self.title = title
        self.originator = originator

        if uuid is None:
            self.uuid = bu.new_uuid()
            logger.debug(f"Created new uuid for object {self}")
        else:
            self.uuid = uuid
            logger.debug(f"Loading existing object {self}")
            self.load_from_xml()
    
    # Define attributes self.part and self.root, using uuid as the primary key

    @property
    def part(self):
        """Part corresponding to self.uuid"""

        if self.uuid is None:
            raise ValueError('Cannot get part if uuid is None')
        return self.model.part_for_uuid(self.uuid)

    @property
    def root(self):
        """Node corresponding to self.uuid"""

        if self.uuid is None:
            raise ValueError('Cannot get root if uuid is None')
        return self.model.root_for_uuid(self.uuid)
    
    @root.setter
    def root(self, value):
        # Only store the new uuid if root is changed
        new_uuid = rqet.uuid_for_part_root(value)
        if new_uuid is None:
            raise ValueError("Cannot set uuid to be None")
        self.uuid = new_uuid

    def load_from_xml(self):
        """Load attributes from XML and HDF5
        
        Loads the attributes as defined in self._attrs
        """

        # Citation block
        self.title = rqet.find_nested_tags_text(self.root_node, ['Citation', 'Title'])
        self.originator = rqet.find_nested_tags_text(self.root_node, ['Citation', 'Originator'])

        # Any other simple attributes
        for attr in self._attrs:
            attr.load(self)

    def create_xml(self, title=None, originator=None, ext_uuid=None):
        """Write XML for all attributes

        Writes to disk the attributes as defined in self._attrs
        
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

    def __eq__(self, other):
        """Implements equals operator. By default, compare objects using uuid"""
        return self.uuid is not None and self.uuid == getattr(other, "uuid", None)

    def __ne__(self, other):
        """Implements not equal operator"""
        return not self.__eq__(other)

    def __repr__(self):
        """String representation"""
        return f"{self.__class__.__name__}(uuid={self.uuid}, title={self.title})"

    def _repr_html_(self):
        """IPython / Jupyter representation"""
        
        keys_to_display = ('uuid', 'title', 'originator')
        html =  f"<h3>{self.__class__.__name__}</h3>\n"
        for key in keys_to_display:
            html += f"<strong>{key}</strong>: {getattr(self, key)}<br>\n"
        return html

    


    # Include some aliases for root, but raise warnings if they are used
    # TODO: remove these aliases for self.node

    @property
    def root_node(self):
        warnings.warn("Attribute 'root_node' is deprecated. Use 'root'", DeprecationWarning)
        return self.root

    @property
    def node(self):
        warnings.warn("Attribute 'node' is deprecated. Sse 'root'", DeprecationWarning)
        return self.root
