from resqpy.olio.base import BaseResqml

class DummyObj(BaseResqml):
    _resqml_obj = 'DummyResqmlInterpretation'

def test_base(example_model):

    # Setup new object
    title = 'Wondermuffin'
    originator = 'Scruffian'
    model, crs = example_model
    dummy = DummyObj(model=model, title=title, originator=originator)

    # Basic attributes and properties
    assert dummy.uuid is not None
    assert dummy.root is not None
    assert dummy.part is not None

    # Comparison with other objects of the same class
    dummy2 = DummyObj(model=model, uuid=dummy.uuid)
    assert dummy == dummy2

    dummy3 = DummyObj(model=model, title=title)
    assert dummy != dummy3
