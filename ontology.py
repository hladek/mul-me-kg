@dataclass
class Evidence:
    source_id: str
    document_title: str
    section_title: str
    text: str
    span_start: int
    span_end: int
    language: str
    summary: str

@dataclass
class Statement:
    evidence: Evidence
    applicability: str # Age, indication, route, organ function, concomitant treatment

@dataclass
class Product:
    name: str
    substance: str
    description: str
    indications: list[Statement]
    contraindications: list[Statement]
    interactions: list[Statement]
    dosage: list[Statement]
    warnings: list[Statement]
