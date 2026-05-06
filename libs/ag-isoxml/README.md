# Ag-ISOXML

Легковесная библиотека для генерации ISOXML (ISO 11783) TaskFile.

## Использование

```python
from ag_isoxml import ISOXMLGenerator

generator = ISOXMLGenerator()
zones = [
    {
        "name": "High Productivity",
        "geometry_wkt": "POLYGON ((...))",
        "rate": 250,
        "color": "#00FF00"
    }
]

xml_content = generator.generate_task_file(
    field_name="North Field",
    field_id="123",
    zones=zones
)

with open("TASKDATA.XML", "w") as f:
    f.write(xml_content)
```
