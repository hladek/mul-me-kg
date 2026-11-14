@dataclass
class Evidence:
    source_id: str
    document_title: str
    section_title: str
    exact_text: str
    span_start: int
    span_end: int
    language: str

@dataclass
class Statement:
    evidence: list[Evidence]
    summary: str

@dataclass
class Indication(Statement):
    condition: [str]
    applicability: [str]
    pupulation: [str]

@dataclass
class DoseRecommandation(Statement):
    dose: str
    frequency: str
    route: str
    duration: str
    treatment_phase: str
    indication: Indication

@dataclass
class AdverseReaction(Statement):
    pass

@dataclass
class Product:
    id: str
    name: str
    manufacturer: str
    substances: list[str]
    description: str
    indications: list[Indication]
    contraindications: list[Indication]
    interactions: list[Statement]
    dosage: list[DoseRecommendation]
    warnings: list[Statement]
