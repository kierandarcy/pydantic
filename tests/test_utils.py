import os
import string
from enum import Enum
from typing import NewType, Union

import pytest

from pydantic import BaseModel
from pydantic.color import Color
from pydantic.dataclasses import dataclass
from pydantic.fields import Undefined
from pydantic.typing import display_as_type, is_new_type, new_type_supertype
from pydantic.utils import ValueItems, deep_update, get_model, import_string, lenient_issubclass, truncate

try:
    import devtools
except ImportError:
    devtools = None


def test_import_module():
    assert import_string('os.path') == os.path


def test_import_module_invalid():
    with pytest.raises(ImportError) as exc_info:
        import_string('xx')
    assert exc_info.value.args[0] == '"xx" doesn\'t look like a module path'


def test_import_no_attr():
    with pytest.raises(ImportError) as exc_info:
        import_string('os.foobar')
    assert exc_info.value.args[0] == 'Module "os" does not define a "foobar" attribute'


@pytest.mark.parametrize('value,expected', ((str, 'str'), ('string', 'str'), (Union[str, int], 'Union[str, int]')))
def test_display_as_type(value, expected):
    assert display_as_type(value) == expected


def test_display_as_type_enum():
    class SubField(Enum):
        a = 1
        b = 'b'

    displayed = display_as_type(SubField)
    assert displayed == 'enum'


def test_display_as_type_enum_int():
    class SubField(int, Enum):
        a = 1
        b = 2

    displayed = display_as_type(SubField)
    assert displayed == 'int'


def test_display_as_type_enum_str():
    class SubField(str, Enum):
        a = 'a'
        b = 'b'

    displayed = display_as_type(SubField)
    assert displayed == 'str'


def test_lenient_issubclass():
    class A(str):
        pass

    assert lenient_issubclass(A, str) is True


def test_lenient_issubclass_is_lenient():
    assert lenient_issubclass('a', 'a') is False


@pytest.mark.parametrize(
    'input_value,output',
    [
        (object, "<class 'object'>"),
        (string.ascii_lowercase, "'abcdefghijklmnopq…'"),
        (list(range(20)), '[0, 1, 2, 3, 4, 5, …'),
    ],
)
def test_truncate(input_value, output):
    with pytest.warns(DeprecationWarning, match='`truncate` is no-longer used by pydantic and is deprecated'):
        assert truncate(input_value, max_len=20) == output


def test_value_items():
    v = ['a', 'b', 'c']
    vi = ValueItems(v, {0, -1})
    assert vi.is_excluded(2)
    assert [v_ for i, v_ in enumerate(v) if not vi.is_excluded(i)] == ['b']

    assert vi.is_included(2)
    assert [v_ for i, v_ in enumerate(v) if vi.is_included(i)] == ['a', 'c']

    v2 = {'a': v, 'b': {'a': 1, 'b': (1, 2)}, 'c': 1}

    vi = ValueItems(v2, {'a': {0, -1}, 'b': {'a': ..., 'b': -1}})

    assert not vi.is_excluded('a')
    assert vi.is_included('a')
    assert not vi.is_excluded('c')
    assert not vi.is_included('c')

    assert str(vi) == "{'a': {0, -1}, 'b': {'a': Ellipsis, 'b': -1}}"
    assert repr(vi) == "ValueItems({'a': {0, -1}, 'b': {'a': Ellipsis, 'b': -1}})"

    excluded = {k_: v_ for k_, v_ in v2.items() if not vi.is_excluded(k_)}
    assert excluded == {'a': v, 'b': {'a': 1, 'b': (1, 2)}, 'c': 1}

    included = {k_: v_ for k_, v_ in v2.items() if vi.is_included(k_)}
    assert included == {'a': v, 'b': {'a': 1, 'b': (1, 2)}}

    sub_v = included['a']
    sub_vi = ValueItems(sub_v, vi.for_element('a'))
    assert repr(sub_vi) == 'ValueItems({0, 2})'

    assert sub_vi.is_excluded(2)
    assert [v_ for i, v_ in enumerate(sub_v) if not sub_vi.is_excluded(i)] == ['b']

    assert sub_vi.is_included(2)
    assert [v_ for i, v_ in enumerate(sub_v) if sub_vi.is_included(i)] == ['a', 'c']


def test_value_items_error():
    with pytest.raises(TypeError) as e:
        ValueItems(1, (1, 2, 3))

    assert str(e.value) == "Unexpected type of exclude value <class 'tuple'>"


def test_is_new_type():
    new_type = NewType('new_type', str)
    new_new_type = NewType('new_new_type', new_type)
    assert is_new_type(new_type)
    assert is_new_type(new_new_type)
    assert not is_new_type(str)


def test_new_type_supertype():
    new_type = NewType('new_type', str)
    new_new_type = NewType('new_new_type', new_type)
    assert new_type_supertype(new_type) == str
    assert new_type_supertype(new_new_type) == str


def test_pretty():
    class MyTestModel(BaseModel):
        a = 1
        b = [1, 2, 3]

    m = MyTestModel()
    assert m.__repr_name__() == 'MyTestModel'
    assert str(m) == 'a=1 b=[1, 2, 3]'
    assert repr(m) == 'MyTestModel(a=1, b=[1, 2, 3])'
    assert list(m.__pretty__(lambda x: f'fmt: {x!r}')) == [
        'MyTestModel(',
        1,
        'a=',
        'fmt: 1',
        ',',
        0,
        'b=',
        'fmt: [1, 2, 3]',
        ',',
        0,
        -1,
        ')',
    ]


def test_pretty_color():
    c = Color('red')
    assert str(c) == 'red'
    assert repr(c) == "Color('red', rgb=(255, 0, 0))"
    assert list(c.__pretty__(lambda x: f'fmt: {x!r}')) == [
        'Color(',
        1,
        "fmt: 'red'",
        ',',
        0,
        'rgb=',
        'fmt: (255, 0, 0)',
        ',',
        0,
        -1,
        ')',
    ]


@pytest.mark.skipif(not devtools, reason='devtools not installed')
def test_devtools_output():
    class MyTestModel(BaseModel):
        a = 1
        b = [1, 2, 3]

    assert devtools.pformat(MyTestModel()) == 'MyTestModel(\n    a=1,\n    b=[1, 2, 3],\n)'


@pytest.mark.skipif(not devtools, reason='devtools not installed')
def test_devtools_output_validation_error():
    class Model(BaseModel):
        a: int

    with pytest.raises(ValueError) as exc_info:
        Model()
    assert devtools.pformat(exc_info.value) == (
        'ValidationError(\n'
        "    model='Model',\n"
        '    errors=[\n'
        '        {\n'
        "            'loc': ('a',),\n"
        "            'msg': 'field required',\n"
        "            'type': 'value_error.missing',\n"
        '        },\n'
        '    ],\n'
        ')'
    )


@pytest.mark.parametrize(
    'mapping, updating_mapping, expected_mapping, msg',
    [
        (
            {'key': {'inner_key': 0}},
            {'other_key': 1},
            {'key': {'inner_key': 0}, 'other_key': 1},
            'extra keys are inserted',
        ),
        (
            {'key': {'inner_key': 0}, 'other_key': 1},
            {'key': [1, 2, 3]},
            {'key': [1, 2, 3], 'other_key': 1},
            'values that can not be merged are updated',
        ),
        (
            {'key': {'inner_key': 0}},
            {'key': {'other_key': 1}},
            {'key': {'inner_key': 0, 'other_key': 1}},
            'values that have corresponding keys are merged',
        ),
        (
            {'key': {'inner_key': {'deep_key': 0}}},
            {'key': {'inner_key': {'other_deep_key': 1}}},
            {'key': {'inner_key': {'deep_key': 0, 'other_deep_key': 1}}},
            'deeply nested values that have corresponding keys are merged',
        ),
    ],
)
def test_deep_update(mapping, updating_mapping, expected_mapping, msg):
    assert deep_update(mapping, updating_mapping) == expected_mapping, msg


def test_deep_update_is_not_mutating():
    mapping = {'key': {'inner_key': {'deep_key': 1}}}
    updated_mapping = deep_update(mapping, {'key': {'inner_key': {'other_deep_key': 1}}})
    assert updated_mapping == {'key': {'inner_key': {'deep_key': 1, 'other_deep_key': 1}}}
    assert mapping == {'key': {'inner_key': {'deep_key': 1}}}


def test_undefined_repr():
    assert repr(Undefined) == 'PydanticUndefined'


def test_get_model():
    class A(BaseModel):
        a: str

    assert get_model(A) == A

    @dataclass
    class B:
        a: str

    assert get_model(B) == B.__pydantic_model__

    class C:
        pass

    with pytest.raises(TypeError):
        get_model(C)
