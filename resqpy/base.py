"""Base class for generic resqml objects """

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Iterable

import resqpy.olio.xml_et as rqet
import resqpy.olio.uuid as bu
import resqpy.olio.weights_and_measures as bwam
from resqpy.olio.xml_namespaces import curly_namespace as ns

@dataclass
class BaseAttribute:
    key: str
    tag: str
    dtype: type
    xml_ns: str = None
    xml_type: str = None
    required: bool = True
    writeable: bool = True

    @abstractmethod
    def load(self, obj):
        raise NotImplementedError

    @abstractmethod
    def write(self, obj):
        raise NotImplementedError


class XmlAttribute(BaseAttribute):
    """Definition of an attribute stored in XML
    
    Args:
        key (str): attribute to be saved to python class
        tag (str): path in XML, possibly nested (e.g. foo/bar)
        dtype (type): One of str, bool, int, float, None
        xml_ns (str): One of xsd or eml, resqml2 
        xml_type: One of positiveInteger
        required (bool): If True, should always be present
    """

    def load(self, obj):
        """Load the value from XML, set as attribute of obj
        
        Args:
            obj: python object for which to load. Must have attribute obj.root
        """

        assert hasattr(obj, 'root')
        tag_list = self.tag.split('/')
        value = rqet.find_nested_tags_cast(obj.root, tag_list, dtype=self.dtype)
        if self.required and value is None:
            raise ValueError(f'Could not load required attribute {self}')
        setattr(obj, self.key, value)

    def write(self, obj):
        """Write the object to XML"""

        if not self.writeable:
            return

        if self.xml_type is None:
            return
        node = obj.root
        assert node is not None

        value = getattr(obj, self.key)

        # Type-specific casting
        if self.xml_type == 'boolean':
            value = str(value).lower()
        elif self.xml_type == 'LengthUom':
            value = bwam.rq_length_unit(value)
        elif self.xml_type == 'PlaneAngleUom':
            if str(value).strip().lower().startswith('deg'):
                value = 'dega'
            else:
                value = 'rad'

        attr_node = rqet.SubElement(node, ns['resqml2'] + self.tag)
        attr_node.set(ns['xsi'] + 'type', ns[self.xml_ns] + self.xml_type)
        attr_node.text = str(value)




class HdfAttribute(BaseAttribute):
    """Definition of an attribute stord in HDF5
    
    Args:
        key (str): attribute to be saved to python class
        tag (str): tag name of HDF5 object
        dtype (type): One of str, bool, int, float, None
        required (bool): If True, should always be present
    """

    def load(self, obj):
        """Load the array from HDF5, set as attribute of obj"""

        model = obj.model
        root = obj.root

        array_node = rqet.find_tag(root, self.tag, must_exist=self.required)
        assert rqet.node_type(array_node) in ['DoubleHdf5Array', 'IntegerHdf5Array', 'Point3dHdf5Array']

        h5_key_pair = model.h5_uuid_and_path_for_node(array_node, tag="Values")
        if h5_key_pair is None: return None
        return model.h5_array_element(h5_key_pair, index=None, cache_array=True,
            dtype=self.dtype, object=obj, array_attribute=self.key)

    def write(self, obj):
        """Write the object to HDF5, set as attribute of obj"""
        
        if self.xml_type is None:
            return 


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
            attr.write(obj=self)
