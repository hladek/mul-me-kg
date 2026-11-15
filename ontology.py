from dataclasses import dataclass


@dataclass
class Evidence:
    source_id: str
    document_title: str | None
    section_title: str | None
    exact_text: str
    span_start: int | None
    span_end: int | None
    language: str | None

@dataclass
class Statement:
    evidence: list[Evidence]
    summary: str

@dataclass
class Pupulation(Statement):
    name: str

@dataclass
class Indication(Statement):
    condition: list[str]
    applicability: list[str] | None
    pupulation: list[Pupulation] | None

@dataclass
class ContraIndication(Statement):
    condition: list[str]
    applicability: list[str] | None
    pupulation: list[Pupulation] | None

@dataclass
class DoseRecommandation(Statement):
    dose: str | None
    frequency: str | None
    route: str | None
    duration: str | None
    treatment_phase: str | None
    indication: Indication | None

@dataclass
class AdverseReaction(Statement):
    event: str
    frequency: str | None
    severity: str | None
    population: list[Pupulation] | None

@dataclass
class Warning(Statement):
    """A warning or precaution, including details explicitly stated in the SmPC."""
    condition: list[str] | None = None
    applicability: list[str] | None = None
    population: list[Pupulation] | None = None
    risk: str | None = None
    recommendation: str | None = None
    monitoring: str | None = None

@dataclass
class Interaction(Statement):
    """An interaction with medicines or substances explicitly stated in the SmPC."""
    interacts_with: list[str] | None = None
    effect: str | None = None
    clinical_consequence: str | None = None
    recommendation: str | None = None
    direction: str | None = None

@dataclass
class Product:
    id: str
    name: str
    manufacturer: str | None
    substances: list[str]
    description: str | None
    indications: list[Indication]
    contraindications: list[ContraIndication]
    interactions: list[Interaction]
    dosage: list[DoseRecommandation]
    warnings: list[Warning]
