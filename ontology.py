"""Dataclasses for extracting source-supported facts from an SmPC.

Process each Summary of Product Characteristics (SmPC) in its source language.
Use the numbered sections identified by ``parse_package_inserts.py`` to populate
the classes below, attaching exact source evidence to every clinical statement.
These classes cover selected product and clinical information, rather than every
SmPC section, and do not themselves perform parsing or runtime validation.

Preserve units, ranges, negation, uncertainty, and population or treatment
qualifiers. Extract only explicitly stated facts; do not infer clinical advice,
translate source values, or calculate doses. Split statements when their
conditions, populations, regimens, or recommendations differ.

Use ``None`` for an optional detail absent or unclear in the processed source.
All constructors accept keyword arguments only. Nullable fields default to None.
For collection fields, an empty list means no items were extracted; it does not
establish that no such facts exist, especially when only part of an SmPC was
processed. Required text fields must be supported by the source, not filled with
invented placeholders. Evidence metadata and Product.id may be supplied by the
ingestion pipeline.
"""

from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Evidence:
    """An exact source excerpt supporting a statement from any SmPC section."""

    # Identifier of the source document in the ingestion pipeline.
    source_id: str
    # Source document title, when available.
    document_title: str | None = None
    # Original section number/title, such as
    # "4.4 Special warnings and precautions for use".
    section_title: str | None = None
    # Supplied parser section identifier, including document index and source
    # location, for example "smpc:1:4.4@1234". Retain it without reconstruction.
    section_id: str | None = None
    # Verbatim excerpt, preserving language, units, and qualifiers.
    exact_text: str
    # Zero-based start character offset in the original document
    # text, when available. Use document offsets rather than chunk offsets.
    span_start: int | None = None
    # Exclusive end character offset in the same text; when both
    # offsets are known, text[span_start:span_end] equals exact_text.
    span_end: int | None = None
    # Source language code, such as "sk" or "en", when known.
    language: str | None = None

@dataclass(kw_only=True)
class Statement:
    """Base for a clinical fact and the source excerpts supporting it."""

    # Excerpts supporting the statement and its populated attributes;
    # retain multiple excerpts when the fact spans source passages.
    evidence: list[Evidence]
    # Concise source-language description preserving the original
    # meaning, including restrictions and conditional wording.
    summary: str

@dataclass(kw_only=True)
class Population(Statement):
    """A patient group explicitly described in the relevant clinical section.

    Inherits evidence and summary from Statement. Populations may qualify
    indications (4.1), dosing (4.2), contraindications (4.3), warnings (4.4),
    reproductive considerations (4.6), or adverse reactions (4.8).
    """

    # Source description of the group, preserving stated age or weight
    # limits, organ impairment, pregnancy status, or other qualifiers.
    name: str

@dataclass(kw_only=True)
class Indication(Statement):
    """A therapeutic indication from SmPC section 4.1.

    Inherits evidence and summary from Statement. Keep distinct treatment
    settings or eligible groups separate when their applicability differs.
    """

    # Diseases or conditions explicitly indicated for treatment or
    # prevention, retaining subtype and stage where stated.
    conditions: list[str]
    # Qualifiers such as treatment line, combination therapy,
    # diagnostic criteria, or other restrictions on the indication.
    applicability: list[str] | None = None
    # Patient groups eligible for this indication, when stated.
    populations: list[Population] | None = None

@dataclass(kw_only=True)
class Contraindication(Statement):
    """An explicit contraindication, primarily from SmPC section 4.3.

    Inherits evidence and summary from Statement. Keep warnings, precautions,
    and monitoring requirements separate unless explicitly contraindicated.
    """

    # Conditions or circumstances prohibiting use, such as a
    # specified hypersensitivity, disease, or concomitant treatment.
    conditions: list[str]
    # Stated qualifiers limiting when the contraindication
    # applies, including thresholds, routes, or treatment combinations.
    applicability: list[str] | None = None
    # Patient groups to which the contraindication applies.
    populations: list[Population] | None = None

@dataclass(kw_only=True)
class DoseRecommendation(Statement):
    """One regimen or administration instruction from SmPC section 4.2.

    Inherits evidence and summary from Statement. Separate regimens that differ
    by indication, population, route, or treatment phase. Populate the dedicated
    fields only when the source explicitly associates them with this regimen.
    """

    # Stated amount, units, range, or weight/body-surface-area basis;
    # preserve the source expression without conversion or calculation.
    dose: str | None = None
    # Administration frequency or timing, including stated limits.
    frequency: str | None = None
    # Route or method of administration as described in the source.
    route: str | None = None
    # Stated treatment length or stopping criteria.
    duration: str | None = None
    # Phase such as initiation, titration, or maintenance.
    treatment_phase: str | None = None
    # Associated therapeutic indication, only when the source
    # explicitly links it to this regimen.
    indication: Indication | None = None
    # Patient groups to which this regimen applies, including stated age,
    # weight, or organ-function restrictions from section 4.2.
    populations: list[Population] | None = None
    # Stated titration, dose adjustment, or missed-dose instructions. Preserve
    # thresholds and conditional wording without calculating a revised dose.
    adjustment: str | None = None
    # Preparation, administration technique, or timing instructions from
    # section 4.2, including relation to food when explicitly stated.
    administration_instructions: str | None = None

@dataclass(kw_only=True)
class AdverseReaction(Statement):
    """An undesirable effect from SmPC section 4.8.

    Inherits evidence and summary from Statement. Preserve distinctions between
    observed reactions, reported events, and uncertain associations.
    """

    # Source name of the reaction or event, retaining its specificity.
    event: str
    # Stated frequency category or numerical estimate, including
    # "not known" when explicitly reported; None means not extracted.
    frequency: str | None = None
    # Explicitly stated intensity or grade; do not infer severity
    # from frequency or equate clinical seriousness with intensity.
    severity: str | None = None
    # Patient groups specifically associated with this reaction.
    populations: list[Population] | None = None

@dataclass(kw_only=True)
class Warning(Statement):
    """A warning or precaution, primarily from SmPC section 4.4.

    Inherits evidence and summary from Statement. Explicit precautions from
    sections 4.6 (fertility, pregnancy and lactation) and 4.7 (driving and machine
    use) can also be represented here, retaining their actual source section.
    """

    # Conditions or circumstances triggering the precaution.
    conditions: list[str] | None = None
    # Stated qualifiers such as route, exposure, treatment
    # timing, or concomitant therapy.
    applicability: list[str] | None = None
    # Patient groups to which the warning applies.
    populations: list[Population] | None = None
    # Potential harm or complication explicitly described by the source.
    risk: str | None = None
    # Stated action, avoidance, interruption, or precaution.
    recommendation: str | None = None
    # Stated clinical or laboratory monitoring, including timing
    # and thresholds where supplied.
    monitoring: str | None = None

@dataclass(kw_only=True)
class Interaction(Statement):
    """An interaction from SmPC section 4.5.

    Inherits evidence and summary from Statement. Use separate instances when
    interacting substances, effects, or recommendations differ. The inherited
    summary holds the interaction description used by the extraction prompt.
    """
    # Named medicines, classes, foods, or other substances;
    # preserve class wording and include examples only when stated.
    interacts_with: list[str] | None = None
    # Stated pharmacokinetic or pharmacodynamic effect.
    effect: str | None = None
    # Explicit clinical outcome or risk of interaction.
    clinical_consequence: str | None = None
    # Stated avoidance, monitoring, dose adjustment, or other
    # management instruction, preserving conditional wording.
    recommendation: str | None = None
    # Stated increase/decrease or other direction of the effect;
    # identify the affected substance or parameter in the source wording.
    direction: str | None = None

@dataclass(kw_only=True)
class Product:
    """Product identity and clinical statements collected from one SmPC.

    Clinical entries retain provenance through Statement.evidence; product
    identity fields use identity_evidence. Empty collections mean no extracted
    entries, not confirmed absence, especially for partially processed sources.
    Other SmPC sections need additional modelling rather than being forced into
    an unrelated clinical category.
    """

    # Stable product identifier assigned by the ingestion pipeline; this
    # is not necessarily a marketing authorisation number (section 8).
    id: str
    # Medicinal product name from section 1, preserving stated strength
    # and pharmaceutical form when part of the name.
    name: str
    # Manufacturer only when explicitly identified in the
    # supplied material. Do not substitute the marketing authorisation
    # holder from section 7 unless also identified as the manufacturer.
    manufacturer: str | None = None
    # Active substances from section 2. Do not silently mix in
    # excipients from section 6.1; retain source substance names.
    substances: list[str] = field(default_factory=list)
    # Source-supported product description, typically the
    # pharmaceutical form and appearance from section 3.
    description: str | None = None
    # Pharmaceutical form explicitly stated in section 3; keep the original
    # wording rather than inferring the form from administration instructions.
    pharmaceutical_form: str | None = None
    # Marketing authorisation holder named in section 7. This organisation
    # must not be assumed to be the manufacturer.
    marketing_authorisation_holder: str | None = None
    # Evidence keyed by identity field name: name, manufacturer, substances,
    # description, pharmaceutical_form, or marketing_authorisation_holder.
    # Each entry holds the excerpts supporting that field's extracted values.
    identity_evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    # Therapeutic indications from section 4.1.
    indications: list[Indication] = field(default_factory=list)
    # Explicit contraindications from section 4.3.
    contraindications: list[Contraindication] = field(default_factory=list)
    # Medicine/substance interactions from section 4.5.
    interactions: list[Interaction] = field(default_factory=list)
    # Regimens and administration instructions from section 4.2.
    dosage: list[DoseRecommendation] = field(default_factory=list)
    # Warnings and precautions from section 4.4, plus explicitly
    # represented precautions from sections 4.6 and 4.7.
    warnings: list[Warning] = field(default_factory=list)
    # Undesirable effects from section 4.8, with stated frequency, severity,
    # and affected patient groups retained in each reaction.
    adverse_reactions: list[AdverseReaction] = field(default_factory=list)
