"""Base class for generic resqml objects """

from abc import ABCMeta, abstractmethod

import resqpy.olio.xml_et as rqet

class BaseAttribute:
    def __init__(self, key, tag, dtype=None, required=True):
        self.key = key
        self.tag = tag
        self.dtype = dtype
        self.required = required

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

        
        pass  # TODO


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

        array_node = rqet.find_tag(obj.root, self.tag, must_exist=self.required)
        _load_hdf5_array(obj, array_node, self.tag)

    def write(self, obj):
        """Write the object to HDF5"""
        pass  # TODO


class BaseResqml(metaclass=ABCMeta):
    """Base class for generic RESQML objects"""

    _attrs: tuple[BaseAttribute] = ()

    def __init__(self, model, title, originator=None):
        self.model = model
        self.title = title
        self.originator = originator

    @property
    @abstractmethod
    def uuid(self):
        # Must be overridden in child classes
        raise NotImplementedError

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
        return self.model.root_for_uuid(self.uuid)

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

    def create_xml(self):
        """Write XML for object"""

        assert self.uuid is not None

        node = self.model.new_obj_node(self._resqml_obj)
        node.attrib['uuid'] = str(self.uuid)

        self.model.create_citation(
            root=node, title=self.title, originator=self.originator
        )

        for attr in self._attrs:
            attr.write(self)


def _load_hdf5_array(object, node, array_attribute, tag = 'Values', dtype = 'float', model = None):
   """Loads the property array data as an attribute of object, from the hdf5 referenced in xml node. """

   assert(rqet.node_type(node) in ['DoubleHdf5Array', 'IntegerHdf5Array', 'Point3dHdf5Array'])
   if model is None: model = object.model
   h5_key_pair = model.h5_uuid_and_path_for_node(node, tag = tag)
   if h5_key_pair is None: return None
   return model.h5_array_element(h5_key_pair, index = None, cache_array = True, dtype = dtype,
                                 object = object, array_attribute = array_attribute)
