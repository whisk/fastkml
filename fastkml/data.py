# Copyright (C) 2022  Christian Ledermann
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
"""Add Custom Data"""
import logging
from dataclasses import dataclass
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from typing import overload

import fastkml.config as config
from fastkml.base import _BaseObject
from fastkml.base import _XMLObject
from fastkml.enums import DataType
from fastkml.enums import Verbosity
from fastkml.exceptions import KMLSchemaError
from fastkml.types import Element

__all__ = [
    "Data",
    "ExtendedData",
    "Schema",
    "SchemaData",
    "SchemaDataDictInput",
    "SchemaDataInput",
    "SchemaDataListInput",
    "SchemaDataOutput",
    "SchemaDataTupleInput",
    "SchemaDataType",
    "SimpleField",
]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimpleField:
    """
    A SimpleField always has both name and type attributes.

    The declaration of the custom field, must specify both the type
    and the name of this field.
    If either the type or the name is omitted, the field is ignored.

    The type can be one of the following:
     - string
     - int
     - uint
     - short
     - ushort
     - float
     - double
     - bool

    The displayName, if any, to be used when the field name is displayed to
    the Google Earth user. Use the [CDATA] element to escape standard
    HTML markup.
    """

    name: str
    type: DataType
    display_name: Optional[str] = None


class Schema(_BaseObject):
    """
    Specifies a custom KML schema that is used to add custom data to
    KML Features.
    The "id" attribute is required and must be unique within the KML file.
    <Schema> is always a child of <Document>.
    """

    __name__ = "Schema"

    def __init__(
        self,
        ns: Optional[str] = None,
        id: Optional[str] = None,
        target_id: Optional[str] = None,
        name: Optional[str] = None,
        fields: Optional[Iterable[SimpleField]] = None,
    ) -> None:
        if id is None:
            raise KMLSchemaError("Id is required for schema")
        super().__init__(ns=ns, id=id, target_id=target_id)
        self.name = name
        self._simple_fields = list(fields) if fields else []

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"ns={self.ns!r}, "
            f"id={self.id!r}, "
            f"target_id={self.target_id!r}, "
            f"name={self.name}, "
            f"fields={self.simple_fields!r}"
            ")"
        )

    @property
    def simple_fields(self) -> Tuple[SimpleField, ...]:
        return tuple(self._simple_fields)

    @simple_fields.setter
    def simple_fields(self, fields: Iterable[SimpleField]) -> None:
        self._simple_fields = list(fields)

    def append(self, field: SimpleField) -> None:
        """Append a field."""
        self._simple_fields.append(field)

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.name = element.get("name")
        simple_fields = element.findall(f"{self.ns}SimpleField")
        for simple_field in simple_fields:
            sfname = simple_field.get("name")
            sftype = simple_field.get("type")
            display_name = simple_field.find(f"{self.ns}displayName")
            sfdisplay_name = display_name.text if display_name is not None else None
            self.append(SimpleField(sfname, DataType(sftype), sfdisplay_name))

    def etree_element(
        self,
        precision: Optional[int] = None,
        verbosity: Verbosity = Verbosity.normal,
    ) -> Element:
        element = super().etree_element(precision=precision, verbosity=verbosity)
        if self.name:
            element.set("name", self.name)
        for simple_field in self.simple_fields:
            sf = config.etree.SubElement(  # type: ignore[attr-defined]
                element, f"{self.ns}SimpleField"
            )
            sf.set("type", simple_field.type.value)
            sf.set("name", simple_field.name)
            if simple_field.display_name:
                dn = config.etree.SubElement(  # type: ignore[attr-defined]
                    sf, f"{self.ns}displayName"
                )
                dn.text = simple_field.display_name
        return element


class Data(_XMLObject):
    """Represents an untyped name/value pair with optional display name."""

    __name__ = "Data"

    def __init__(
        self,
        ns: Optional[str] = None,
        name: Optional[str] = None,
        value: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> None:
        super().__init__(ns)

        self.name = name
        self.value = value
        self.display_name = display_name

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"ns='{self.ns}',"
            f"name='{self.name}', value='{self.value}'"
            f"display_name='{self.display_name}')"
        )

    def etree_element(
        self,
        precision: Optional[int] = None,
        verbosity: Verbosity = Verbosity.normal,
    ) -> Element:
        element = super().etree_element(precision=precision, verbosity=verbosity)
        element.set("name", self.name or "")
        value = config.etree.SubElement(  # type: ignore[attr-defined]
            element, f"{self.ns}value"
        )
        value.text = self.value
        if self.display_name:
            display_name = config.etree.SubElement(  # type: ignore[attr-defined]
                element, f"{self.ns}displayName"
            )
            display_name.text = self.display_name
        return element

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.name = element.get("name")
        tmp_value = element.find(f"{self.ns}value")
        if tmp_value is not None:
            self.value = tmp_value.text
        display_name = element.find(f"{self.ns}displayName")
        if display_name is not None:
            self.display_name = display_name.text


class ExtendedData(_XMLObject):
    """Represents a list of untyped name/value pairs. See docs:

    -> 'Adding Untyped Name/Value Pairs'
       https://developers.google.com/kml/documentation/extendeddata

    """

    __name__ = "ExtendedData"

    def __init__(
        self,
        ns: Optional[str] = None,
        elements: Optional[List[Union[Data, "SchemaData"]]] = None,
    ) -> None:
        super().__init__(ns)
        self.elements = elements or []

    def etree_element(
        self,
        precision: Optional[int] = None,
        verbosity: Verbosity = Verbosity.normal,
    ) -> Element:
        element = super().etree_element(precision=precision, verbosity=verbosity)
        for subelement in self.elements:
            element.append(subelement.etree_element())
        return element

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.elements = []
        untyped_data = element.findall(f"{self.ns}Data")
        for ud in untyped_data:
            el_data = Data(self.ns)
            el_data.from_element(ud)
            self.elements.append(el_data)
        typed_data = element.findall(f"{self.ns}SchemaData")
        for sd in typed_data:
            el_schema_data = SchemaData(self.ns, "dummy")
            el_schema_data.from_element(sd)
            self.elements.append(el_schema_data)


SchemaDataType = List[Dict[str, Union[int, str]]]
SchemaDataListInput = List[Union[Dict[str, str], SchemaDataType]]
SchemaDataTupleInput = Tuple[Union[Dict[str, str], Tuple[Dict[str, Union[int, str]]]]]
SchemaDataDictInput = Dict[str, Union[int, str]]
SchemaDataInput = Optional[
    Union[
        SchemaDataListInput,
        SchemaDataTupleInput,
        SchemaDataDictInput,
    ]
]
SchemaDataOutput = Tuple[Dict[str, Union[int, str]], ...]


class SchemaData(_XMLObject):
    """
    <SchemaData schemaUrl="anyURI">
    This element is used in conjunction with <Schema> to add typed
    custom data to a KML Feature. The Schema element (identified by the
    schemaUrl attribute) declares the custom data type. The actual data
    objects ("instances" of the custom data) are defined using the
    SchemaData element.
    The <schemaURL> can be a full URL, a reference to a Schema ID defined
    in an external KML file, or a reference to a Schema ID defined
    in the same KML file.
    """

    __name__ = "SchemaData"

    def __init__(
        self,
        ns: Optional[str] = None,
        schema_url: Optional[str] = None,
        data: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        super().__init__(ns)
        if (not isinstance(schema_url, str)) or (not schema_url):
            raise ValueError("required parameter schema_url missing")
        self.schema_url = schema_url
        self._data: SchemaDataType = []
        self.data = data  # type: ignore[assignment]

    @property
    def data(self) -> SchemaDataOutput:
        return tuple(self._data)

    @data.setter
    @overload
    def data(self, data: SchemaDataListInput) -> None:
        ...

    @data.setter
    @overload
    def data(self, data: SchemaDataTupleInput) -> None:
        ...

    @data.setter
    @overload
    def data(self, data: SchemaDataDictInput) -> None:
        ...

    @data.setter
    def data(self, data: SchemaDataInput) -> None:
        if isinstance(data, (tuple, list)):
            self._data = []
            for d in data:
                if isinstance(d, (tuple, list)):
                    self.append_data(*d)
                elif isinstance(d, dict):
                    self.append_data(**d)
        elif data is None:
            self._data = []
        else:
            raise TypeError("data must be of type tuple or list")

    def append_data(self, name: str, value: Union[int, str]) -> None:
        if isinstance(name, str) and name:
            self._data.append({"name": name, "value": value})
        else:
            raise TypeError("name must be a nonempty string")

    def etree_element(
        self,
        precision: Optional[int] = None,
        verbosity: Verbosity = Verbosity.normal,
    ) -> Element:
        element = super().etree_element(precision=precision, verbosity=verbosity)
        element.set("schemaUrl", self.schema_url)
        for data in self.data:
            sd = config.etree.SubElement(  # type: ignore[attr-defined]
                element, f"{self.ns}SimpleData"
            )
            sd.set("name", data["name"])
            sd.text = data["value"]
        return element

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.data = []  # type: ignore[assignment]
        self.schema_url = element.get("schemaUrl")
        simple_data = element.findall(f"{self.ns}SimpleData")
        for sd in simple_data:
            self.append_data(sd.get("name"), sd.text)
