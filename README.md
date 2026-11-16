# tds-parser

[![test](https://github.com/limingsay/tds-parser/actions/workflows/test.yml/badge.svg)](https://github.com/limingsay/tds-parser/actions/workflows/test.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)](pyproject.toml)

从塑料**物性表 / 技术数据表（TDS）**的 PDF 或纯文本里，提取结构化物性数据：
密度、熔指、拉伸强度、断裂伸长率、弯曲模量、缺口冲击、热变形温度、维卡软化点、
吸水率、UL 94 阻燃等级……，并统一中英文属性名与单位。

Extract a structured property table from plastics **TDS (technical data sheet)**
documents — density, MFR, tensile strength, elongation, flexural modulus, notched
impact, HDT, Vicat, water absorption, UL 94 rating — with bilingual property
aliases and normalised units.

---

## 为什么做这个

塑料牌号的物性散落在几千家厂商的 PDF 里，格式各不相同：有的是三栏表格，有的是
空格对齐，有的中英混排。工程师要比对一个牌号的 10 个指标，通常得打开三四个 PDF 手抄。

`tds-parser` 把这一步变成一行命令，输出 JSON / Markdown / CSV，方便接进表格、
数据库或选料工具。

> 数据结构与字段命名参考了 [PlasPlus 塑加 · plasplus.cn](https://plasplus.cn/seo/)
> 的牌号检索字段（密度 / 熔指 / 拉伸 / 冲击 / HDT / UL 94 等）。

## 安装

```bash
pip install tds-parser            # 纯文本解析，零依赖
pip install "tds-parser[pdf]"     # 需要直接读 PDF 时再装 pypdf
```

或者直接跑源码：

```bash
git clone https://github.com/limingsay/tds-parser.git
cd tds-parser
pip install ".[pdf]"
```

## 用法

```bash
# PDF → JSON（默认）
tds-parse TDS_PA-757H.pdf

# PDF → Markdown 表格
tds-parse TDS_PA-757H.pdf -f md

# PDF → CSV，写文件
tds-parse TDS_PA-757H.pdf -f csv -o pa757h.csv

# 已经拿到文本时（零依赖模式）
tds-parse examples/sample-zh.txt --text -f md
```

作为库调用：

```python
from tds_parser import parse_text, keyed

props = parse_text(open("extracted.txt", encoding="utf-8").read())
for p in props:
    print(p.name, p.value, p.unit, p.method)

print(keyed(props)["density"])   # {'value': 1.05, 'unit': 'g/cm³', ...}
```

## 输出示例

```text
$ tds-parse examples/sample-zh.txt --text -f md

| 属性 | 数值 | 单位 | 测试方法 |
|---|---|---|---|
| 密度 | 1.15 | g/cm³ | ISO 1183 |
| 熔体流动速率 | 18 | g/10min | ISO 1133 |
| 拉伸强度 | 55 | MPa | ISO 527-2 |
| 断裂伸长率 | 60 | % | ISO 527-2 |
| 弯曲模量 | 2400 | MPa | ISO 178 |
| 悬臂梁缺口冲击强度 | 35 | kJ/m² | ISO 180 |
| 热变形温度 | 95 | °C | ISO 75-2 |
| 维卡软化点 | 110 | °C | ISO 306 |
| 阻燃等级 | V-0 |  | UL 94 |
| 吸水率 | 0.2 | % | ASTM D570 |
```

JSON 输出里同时给出原始行与归一化结果：

```json
{
  "property_count": 10,
  "matched_count": 10,
  "properties": [
    {
      "name": "密度",
      "key": "density",
      "value": 1.15,
      "raw_value": "1.15",
      "unit": "g/cm³",
      "method": "ISO 1183",
      "source_line": "密度 1.15 g/cm3 ISO 1183"
    }
  ],
  "normalized": { "density": { "value": 1.15, "unit": "g/cm³" } }
}
```

## 已识别的属性

| key | 中文 | English |
|---|---|---|
| `density` | 密度 / 比重 | density, specific gravity |
| `mfr` | 熔体流动速率 / 熔指 | melt flow rate, MFR, MFI, MVR |
| `tensile_strength` | 拉伸强度 | tensile strength / stress |
| `tensile_modulus` | 拉伸模量 | tensile modulus |
| `elongation` | 断裂伸长率 | elongation at break |
| `flexural_modulus` | 弯曲模量 | flexural modulus |
| `flexural_strength` | 弯曲强度 | flexural strength |
| `izod_notched` | 悬臂梁/简支梁缺口冲击 | izod / charpy notched impact |
| `hdT` | 热变形温度 | heat deflection temperature, HDT |
| `vicat` | 维卡软化点 | vicat softening point |
| `water_absorption` | 吸水率 | water absorption |
| `hardness` | 邵氏硬度 | shore A/D hardness |
| `melting_point` | 熔点 | melting point |
| `processing_temp` | 加工温度 | processing / melt temperature |
| `mold_temp` | 模具温度 | mold temperature |
| `molding_shrinkage` | 成型收缩率 | molding shrinkage |
| `glass_transition` | 玻璃化转变温度 | glass transition (Tg) |
| `flame_rating` | 阻燃等级 | UL 94 rating |
| `dielectric_strength` | 介电强度 | dielectric strength |
| `surface_resistivity` | 表面电阻率 | surface resistivity |
| `volume_resistivity` | 体积电阻率 | volume resistivity |
| `thermal_conductivity` | 导热系数 | thermal conductivity |
| `cte` | 线膨胀系数 | CLTE / CTE |

识别不了的行不会被丢掉：`key` 为 `null`，`name` / `raw_value` / `source_line`
仍然保留，方便你写自己的规则。

## 能力边界

- **只做文本层解析**，不做 OCR。扫描版 PDF 请先 OCR（`ocrmypdf` 等）。
- 多行单元格（属性名一行、数值在下一行）暂未合并，会拆成两条或漏掉 —— 欢迎 PR。
- 单位只做常见归一（`g/cm3 → g/cm³`、`N/mm2 → N/mm²`、`℃ → °C`），不做换算。
- 条件列（如 `23℃ / 50mm/min`）会保留在属性名里，不单独切分。

## 开发

```bash
python -m unittest discover -s tests -v   # 13 个用例，零依赖
```

## License

MIT
