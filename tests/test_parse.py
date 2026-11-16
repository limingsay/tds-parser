"""Unit tests for the TDS parser (no external dependencies)."""
import unittest

from tds_parser import parse_text, normalize_name, to_csv, to_json, to_markdown
from tds_parser.parse import parse_line, keyed


CHINESE_TDS = """\
技术数据表  PA-757H  产品信息
密度                      1.05 g/cm3          ISO 1183
熔体流动速率              22 g/10min          ISO 1133
拉伸强度                  47 MPa              ASTM D638
断裂伸长率                25 %                ASTM D638
弯曲模量                  2500 MPa            ASTM D790
悬臂梁缺口冲击强度        20 kJ/m2            ASTM D256
热变形温度                85 °C               ASTM D648
维卡软化点                105 °C              ISO 306
吸水率                    0.2 %               ASTM D570
成型收缩率                0.4 %               ASTM D955
阻燃等级                  UL 94 V-0
第 1 页 / 共 2 页
"""

ENGLISH_TDS = """\
Technical Data Sheet — Technical Data Sheet
Property                    Value            Unit        Method
Density                     1.14             g/cm3       ASTM D792
Melt Flow Rate              8                g/10 min    ASTM D1238
Tensile Strength            60               MPa         ISO 527-2
Elongation at Break         120              %           ISO 527-2
Flexural Modulus            2300             MPa         ISO 178
Izod Notched Impact         45               J/m         ASTM D256
Heat Deflection Temperature 95               °C          ASTM D648
Water Absorption            0.15             %           ASTM D570
Flame rating                UL 94 V0

Copyright © 2026 Somebody
"""


class NormalizeTest(unittest.TestCase):
    def test_chinese_aliases(self):
        self.assertEqual(normalize_name("密度"), "density")
        self.assertEqual(normalize_name("熔体流动速率"), "mfr")
        self.assertEqual(normalize_name("悬臂梁缺口冲击强度"), "izod_notched")
        self.assertEqual(normalize_name("热变形温度"), "hdT")

    def test_english_aliases(self):
        self.assertEqual(normalize_name("Density"), "density")
        self.assertEqual(normalize_name("Melt Flow Rate (MFR)"), "mfr")
        self.assertEqual(normalize_name("Tensile Stress at Break"), "tensile_strength")
        self.assertEqual(normalize_name("Heat Deflection Temperature"), "hdT")

    def test_unknown_returns_none(self):
        self.assertIsNone(normalize_name("备注信息"))
        self.assertIsNone(normalize_name(""))


class ParseLineTest(unittest.TestCase):
    def test_chinese_line(self):
        prop = parse_line("密度                      1.05 g/cm3          ISO 1183")
        self.assertIsNotNone(prop)
        self.assertEqual(prop.key, "density")
        self.assertAlmostEqual(prop.value, 1.05)
        self.assertEqual(prop.unit, "g/cm³")
        self.assertEqual(prop.method, "ISO 1183")

    def test_english_line_single_space_columns(self):
        prop = parse_line("Tensile Strength            60               MPa         ISO 527-2")
        self.assertIsNotNone(prop)
        self.assertEqual(prop.key, "tensile_strength")
        self.assertAlmostEqual(prop.value, 60.0)
        self.assertEqual(prop.unit, "MPa")

    def test_less_than_prefix_is_kept_in_raw(self):
        prop = parse_line("Water Absorption   <0.01 %  ASTM D570")
        self.assertIsNotNone(prop)
        self.assertEqual(prop.raw_value, "<0.01")
        self.assertAlmostEqual(prop.value, 0.01)

    def test_range_keeps_first_number(self):
        prop = parse_line("Melting Point  160-170 °C  DSC")
        self.assertIsNotNone(prop)
        self.assertAlmostEqual(prop.value, 160.0)

    def test_flame_rating_without_unit(self):
        prop = parse_line("阻燃等级                  UL 94 V-0")
        self.assertIsNotNone(prop)
        self.assertEqual(prop.key, "flame_rating")
        self.assertEqual(prop.raw_value, "V-0")

    def test_noise_lines_are_skipped(self):
        for line in (
            "第 1 页 / 共 2 页",
            "Technical Data Sheet",
            "版权所有  某某公司",
            "https://example.com/tds.pdf",
            "",
        ):
            self.assertIsNone(parse_line(line), msg=line)

    def test_value_first_layout(self):
        prop = parse_line("85 °C   Heat Deflection Temperature   ASTM D648")
        self.assertIsNotNone(prop)
        self.assertEqual(prop.key, "hdT")


class ParseDocumentTest(unittest.TestCase):
    def test_chinese_document(self):
        props = parse_text(CHINESE_TDS)
        got = keyed(props)
        self.assertEqual(got["density"]["value"], 1.05)
        self.assertEqual(got["mfr"]["unit"], "g/10min")
        self.assertEqual(got["flame_rating"]["raw_value"], "V-0")
        self.assertGreaterEqual(len(props), 10)

    def test_english_document(self):
        props = parse_text(ENGLISH_TDS)
        got = keyed(props)
        self.assertEqual(got["density"]["value"], 1.14)
        self.assertEqual(got["hdT"]["method"], "ASTM D648")
        self.assertGreaterEqual(len(props), 8)
        # the copyright footer must not become a property
        self.assertFalse(any("Copyright" in p.name for p in props))

    def test_serialisers_round_trip(self):
        props = parse_text(CHINESE_TDS)
        self.assertIn("density", to_json(props))
        self.assertIn("| 密度", to_markdown(props))
        self.assertTrue(to_csv(props).startswith("name,key,value"))


if __name__ == "__main__":
    unittest.main()
