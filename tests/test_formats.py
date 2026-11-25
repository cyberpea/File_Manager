import xml.etree.ElementTree as ET

import pytest

from file_manager.config import JSON_MAX_DEPTH, XML_MAX_DEPTH
from file_manager.files import create_file, read_file, list_files
from file_manager.formats import read_json, write_json, read_xml, write_xml

XXE = b"""<?xml version="1.0"?>
<!DOCTYPE data [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<data>&xxe;</data>"""

BILLION_LAUGHS = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
<!ENTITY lol "lol">
<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<lolz>&lol4;</lolz>"""

HARMLESS_DTD = b"""<?xml version="1.0"?>
<!DOCTYPE note [<!ELEMENT note (#PCDATA)>]>
<note>text</note>"""


def test_json_roundtrip(user_id):
    obj = {"имя": "Вика", "курс": 3, "оценки": [5, 4.5, None, True]}
    write_json(user_id, "data.json", obj)
    assert read_json(user_id, "data.json") == obj


def test_json_overwrite(user_id):
    write_json(user_id, "data.json", {"version": 1})
    write_json(user_id, "data.json", {"version": 2}, overwrite=True)
    assert read_json(user_id, "data.json") == {"version": 2}


@pytest.mark.parametrize("content", [
    b"{not json}",
    b"",
    b'{"a": 1,}',
    b"\xff\xfe\x00",
    b'{"a": NaN}',
    b'{"a": Infinity}',
    b'{"a": -Infinity}',
    b'{"a": 1e999}',
    b'{"a": -1e999}',
])
def test_invalid_json_is_rejected(user_id, content):
    create_file(user_id, "data.json", content)
    with pytest.raises(ValueError):
        read_json(user_id, "data.json")


def test_json_at_max_depth_is_accepted(user_id):
    content = b"[" * JSON_MAX_DEPTH + b"]" * JSON_MAX_DEPTH
    create_file(user_id, "deep.json", content)
    read_json(user_id, "deep.json")


def test_too_deep_json_is_rejected(user_id, events):
    depth = JSON_MAX_DEPTH + 1
    create_file(user_id, "deep.json", b"[" * depth + b"]" * depth)
    with pytest.raises(ValueError):
        read_json(user_id, "deep.json")
    assert events() == [("limit_exceeded", repr("deep.json"))]


def test_extremely_deep_json_is_rejected(user_id):
    depth = 100_000
    create_file(user_id, "deep.json", b"[" * depth + b"]" * depth)
    with pytest.raises(ValueError):
        read_json(user_id, "deep.json")


def test_too_deep_object_is_not_written(user_id):
    obj = []
    for level in range(JSON_MAX_DEPTH):
        obj = [obj]
    with pytest.raises(ValueError):
        write_json(user_id, "deep.json", obj)
    assert list_files(user_id) == []


def test_cyclic_object_is_not_written(user_id):
    obj = []
    obj.append(obj)
    with pytest.raises(ValueError):
        write_json(user_id, "cycle.json", obj)


@pytest.mark.parametrize("obj", [
    {1, 2, 3},
    b"bytes",
    float("nan"),
    float("inf"),
    {"key": object()},
])
def test_unsupported_object_is_not_written_as_json(user_id, obj):
    with pytest.raises(ValueError):
        write_json(user_id, "data.json", obj)
    assert list_files(user_id) == []


def test_xml_is_read(user_id):
    create_file(user_id, "ok.xml", "<note id='1'><to>Вика</to></note>".encode("utf-8"))
    root = read_xml(user_id, "ok.xml")
    assert root.tag == "note"
    assert root.attrib == {"id": "1"}
    assert root[0].text == "Вика"


def test_xxe_is_rejected(user_id, events):
    create_file(user_id, "xxe.xml", XXE)
    with pytest.raises(ValueError):
        read_xml(user_id, "xxe.xml")
    assert events() == [("access_denied", repr("xxe.xml"))]


def test_billion_laughs_is_rejected(user_id, events):
    create_file(user_id, "laughs.xml", BILLION_LAUGHS)
    with pytest.raises(ValueError):
        read_xml(user_id, "laughs.xml")
    assert events() == [("access_denied", repr("laughs.xml"))]


def test_any_dtd_is_rejected(user_id):
    create_file(user_id, "dtd.xml", HARMLESS_DTD)
    with pytest.raises(ValueError):
        read_xml(user_id, "dtd.xml")


@pytest.mark.parametrize("content", [
    b"<a><b></a>",
    b"",
    b"just text",
    b"<?xml version='1.0' encoding='no-such-encoding'?><a/>",
    b"<a>\x00</a>",
])
def test_invalid_xml_is_rejected(user_id, content):
    create_file(user_id, "bad.xml", content)
    with pytest.raises(ValueError):
        read_xml(user_id, "bad.xml")


def test_xml_at_max_depth_is_accepted(user_id):
    content = b"<a>" * XML_MAX_DEPTH + b"</a>" * XML_MAX_DEPTH
    create_file(user_id, "deep.xml", content)
    read_xml(user_id, "deep.xml")


def test_too_deep_xml_is_rejected(user_id, events):
    depth = XML_MAX_DEPTH + 1
    create_file(user_id, "deep.xml", b"<a>" * depth + b"</a>" * depth)
    with pytest.raises(ValueError):
        read_xml(user_id, "deep.xml")
    assert events() == [("limit_exceeded", repr("deep.xml"))]


def test_xml_roundtrip(user_id):
    root = ET.Element("note")
    root.set("id", "1")
    child = ET.SubElement(root, "to")
    child.text = "Вика <b>&</b>"
    write_xml(user_id, "note.xml", root)
    loaded = read_xml(user_id, "note.xml")
    assert loaded.tag == "note"
    assert loaded.attrib == {"id": "1"}
    assert loaded[0].text == "Вика <b>&</b>"
    assert len(loaded[0]) == 0


@pytest.mark.parametrize("bad_tag", [
    "a/><admin>true</admin><b",
    "a b",
    "1abc",
    "",
    "тег",
    "a" * 65,
    None,
    42,
])
def test_bad_tag_name_is_not_written(user_id, bad_tag):
    root = ET.Element("root")
    ET.SubElement(root, "ok").append(ET.Element(bad_tag))
    with pytest.raises(ValueError):
        write_xml(user_id, "data.xml", root)
    assert list_files(user_id) == []


def test_bad_attribute_name_is_not_written(user_id):
    root = ET.Element("root")
    root.set('a="1" admin', "true")
    with pytest.raises(ValueError):
        write_xml(user_id, "data.xml", root)
    assert list_files(user_id) == []


def test_attribute_value_is_escaped(user_id):
    root = ET.Element("root")
    root.set("name", '"><admin>true</admin><x a="')
    write_xml(user_id, "data.xml", root)
    loaded = read_xml(user_id, "data.xml")
    assert len(loaded) == 0
    assert loaded.attrib == {"name": '"><admin>true</admin><x a="'}


@pytest.mark.parametrize("bad_text", ["a\x00b", "a\x1bb", 42])
def test_unwritable_text_is_not_written(user_id, bad_text):
    root = ET.Element("root")
    root.text = bad_text
    with pytest.raises(ValueError):
        write_xml(user_id, "data.xml", root)
    assert list_files(user_id) == []


def test_not_an_element_is_not_written(user_id):
    with pytest.raises(ValueError):
        write_xml(user_id, "data.xml", "<root/>")


def test_too_deep_tree_is_not_written(user_id):
    root = ET.Element("a")
    current = root
    for level in range(XML_MAX_DEPTH):
        current = ET.SubElement(current, "a")
    with pytest.raises(ValueError):
        write_xml(user_id, "deep.xml", root)
    assert list_files(user_id) == []


def test_written_xml_has_no_doctype(user_id):
    root = ET.Element("root")
    root.text = "<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]>&e;"
    write_xml(user_id, "data.xml", root)
    assert b"<!DOCTYPE" not in read_file(user_id, "data.xml")
    assert read_xml(user_id, "data.xml").text == root.text
