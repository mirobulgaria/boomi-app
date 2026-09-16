"""Generic shape contract extractor for Boomi process configurations.

This module provides structure-only analysis of Boomi process shape
configurations, extracting serialization variants without exposing
business values, credentials, or component identities.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from boomi_builder.services.boomi_process_analyzer import (
    ProcessAnalysis,
    ProcessConfigurationElement,
    ProcessShape,
)


@dataclass(frozen=True)
class ConfigurationStructure:
    """Structure-only representation of XML configuration.

    This captures the hierarchical structure of configuration elements
    without attribute values, element text, or component identities.

    Values are intentionally discarded during construction to prevent
    accidental leakage into models, logs, or AI context.
    """

    element_name: str
    attribute_names: tuple[str, ...] = field(default_factory=tuple)
    children: tuple[ConfigurationStructure, ...] = field(default_factory=tuple)

    def get_structural_paths(
        self,
        prefix: str = "",
    ) -> list[str]:
        """Generate deterministic structural paths from configuration.

        Paths represent the hierarchical structure using element names
        and attribute names, without values.

        Example: configuration/message/@combined
        """
        paths: list[str] = []

        current_path = f"{prefix}/{self.element_name}" if prefix else self.element_name
        paths.append(current_path)

        for attr_name in sorted(self.attribute_names):
            paths.append(f"{current_path}/@{attr_name}")

        for child in self.children:
            paths.extend(
                child.get_structural_paths(prefix=current_path)
            )

        return paths

    def get_observed_cardinalities(
        self,
    ) -> dict[str, dict[str, int]]:
        """Count observed child cardinalities per element path.

        Returns nested mapping: element_path -> {"min": count, "max": count}
        For the current instance, all min == max == actual count.

        This is observational data only, not a Boomi product contract.
        """
        result: dict[str, dict[str, int]] = {}

        if self.children:
            child_name_counts: dict[str, int] = {}
            for child in self.children:
                name = child.element_name
                child_name_counts[name] = child_name_counts.get(name, 0) + 1

            for name, count in child_name_counts.items():
                result[f"{self.element_name}/{name}"] = {
                    "min": count,
                    "max": count,
                }

        for child in self.children:
            result.update(child.get_observed_cardinalities())

        return result


@dataclass(frozen=True)
class ShapeInstanceStructure:
    """Structure-only representation of a single shape instance.

    Contains only structural metadata - no values, text, or identities.
    """

    shape_type: str
    configuration_root_names: tuple[str, ...] = field(default_factory=tuple)
    configuration_structure: ConfigurationStructure | None = None

    def compute_fingerprint(self) -> str:
        """Compute deterministic structural fingerprint.

        The fingerprint is based ONLY on structural information:
        - element names
        - attribute names
        - hierarchy
        - child occurrence counts

        It is intentionally independent of:
        - attribute values
        - element text
        - component IDs
        - labels
        - business values
        """
        if self.configuration_structure is None:
            return f"{self.shape_type}|<no-configuration>"

        return self._compute_structure_fingerprint(
            self.configuration_structure
        )

    def _compute_structure_fingerprint(
        self,
        structure: ConfigurationStructure,
    ) -> str:
        """Recursive fingerprint computation."""
        parts: list[str] = []

        parts.append(f"E:{structure.element_name}")

        if structure.attribute_names:
            sorted_attrs = tuple(sorted(structure.attribute_names))
            parts.append(f"A:({','.join(sorted_attrs)})")

        if structure.children:
            child_fingerprints = tuple(
                sorted(
                    self._compute_structure_fingerprint(child)
                    for child in structure.children
                )
            )
            parts.append(f"C:({'|'.join(child_fingerprints)})")

        return ";".join(parts)


@dataclass(frozen=True)
class ShapeVariant:
    """One unique structural variant observed for a shapetype.

    Multiple shape instances with identical structure map to the same variant.
    """

    variant_id: str
    instance_count: int
    structure: ConfigurationStructure | None
    structural_paths: tuple[str, ...] = field(default_factory=tuple)
    observed_cardinalities: dict[str, dict[str, int]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class ShapeTypeObservation:
    """Aggregate observations for one shapetype across a corpus."""

    shapetype: str
    total_instances: int
    distinct_variants: int
    variants: tuple[ShapeVariant, ...]


@dataclass(frozen=True)
class ShapeContractExtraction:
    """Complete shape contract extraction result."""

    shapetype_observations: tuple[ShapeTypeObservation, ...]
    total_shapes_observed: int
    total_distinct_variants: int


@dataclass(frozen=True)
class ShapeVariantCatalogEntry:
    """Catalog entry for one structural variant across the entire corpus.

    This aggregates instances from multiple process definitions.
    Contains only structural evidence - no values, identities, or raw XML.
    """

    variant_id: str
    instances_observed: int
    structural_fingerprint: str
    structural_paths: tuple[str, ...]
    observed_cardinalities: dict[str, dict[str, int]]


@dataclass(frozen=True)
class ShapeTypeCatalogEntry:
    """Catalog entry for one shapetype across the entire corpus.

    Aggregates all variants and instances from multiple process definitions.
    """

    shapetype: str
    instances_observed: int
    variants: tuple[ShapeVariantCatalogEntry, ...]


@dataclass(frozen=True)
class ShapeContractCatalog:
    """Machine-readable structural catalog aggregated across processes.

    This is a STRUCTURAL EVIDENCE model only.

    Contains NO:
    - Component XML
    - Raw XML fragments
    - Component IDs
    - Component names
    - Folder names
    - User labels
    - Shape labels
    - Attribute values
    - Element text
    - Business values
    - Credentials
    - Secrets
    """

    process_definitions_observed: int
    shapes_observed: int
    shapetypes: tuple[ShapeTypeCatalogEntry, ...]


class BoomiShapeContractExtractor:
    """Extracts generic shape contract structures from process analysis.

    This service operates on ProcessAnalysis results from BoomiProcessAnalyzer
    and produces structure-only contract observations without exposing
    business values, credentials, or component identities.
    """

    def extract(
        self,
        analysis: ProcessAnalysis,
    ) -> ShapeContractExtraction:
        """Extract shape contract structures from process analysis.

        Args:
            analysis: ProcessAnalysis from BoomiProcessAnalyzer

        Returns:
            ShapeContractExtraction with structural variants and observations
        """
        # Convert shapes to structure-only representations
        instance_structures = [
            self._shape_to_instance_structure(shape)
            for shape in analysis.shapes
        ]

        # Group by shapetype
        shapetype_groups: dict[
            str,
            list[ShapeInstanceStructure]
        ] = defaultdict(list)

        for instance in instance_structures:
            shapetype_groups[instance.shape_type].append(instance)

        # Compute variants per shapetype
        shapetype_observations: list[ShapeTypeObservation] = []
        total_variants = 0

        for shapetype in sorted(shapetype_groups.keys()):
            instances = shapetype_groups[shapetype]

            # Group by fingerprint (structural variant)
            fingerprint_groups: dict[
                str,
                list[ShapeInstanceStructure]
            ] = defaultdict(list)

            for instance in instances:
                fingerprint = instance.compute_fingerprint()
                fingerprint_groups[fingerprint].append(instance)

            # Create ShapeVariant objects
            variants: list[ShapeVariant] = []
            variant_counter = 1

            for fingerprint in sorted(fingerprint_groups.keys()):
                group_instances = fingerprint_groups[fingerprint]
                first_instance = group_instances[0]

                # Generate variant ID deterministically
                variant_id = f"variant-{variant_counter:03d}"
                variant_counter += 1

                # Extract structural paths and cardinalities
                if first_instance.configuration_structure is not None:
                    structural_paths = tuple(
                        sorted(
                            first_instance.configuration_structure.get_structural_paths()
                        )
                    )
                    observed_cardinalities = (
                        first_instance.configuration_structure.get_observed_cardinalities()
                    )
                else:
                    structural_paths = ()
                    observed_cardinalities = {}

                variants.append(
                    ShapeVariant(
                        variant_id=variant_id,
                        instance_count=len(group_instances),
                        structure=first_instance.configuration_structure,
                        structural_paths=structural_paths,
                        observed_cardinalities=observed_cardinalities,
                    )
                )

            shapetype_observations.append(
                ShapeTypeObservation(
                    shapetype=shapetype,
                    total_instances=len(instances),
                    distinct_variants=len(variants),
                    variants=tuple(variants),
                )
            )

            total_variants += len(variants)

        return ShapeContractExtraction(
            shapetype_observations=tuple(shapetype_observations),
            total_shapes_observed=len(instance_structures),
            total_distinct_variants=total_variants,
        )

    def _shape_to_instance_structure(
        self,
        shape: ProcessShape,
    ) -> ShapeInstanceStructure:
        """Convert ProcessShape to structure-only representation.

        Values and text are discarded during conversion.
        """
        if not shape.configuration:
            return ShapeInstanceStructure(
                shape_type=shape.shape_type,
                configuration_root_names=(),
                configuration_structure=None,
            )

        # Convert first configuration element (typical Boomi process has one root)
        # If multiple roots exist, this represents the complete structure tree
        structure = self._configuration_element_to_structure(
            shape.configuration[0]
        )

        return ShapeInstanceStructure(
            shape_type=shape.shape_type,
            configuration_root_names=tuple(
                element.name for element in shape.configuration
            ),
            configuration_structure=structure,
        )

    def _configuration_element_to_structure(
        self,
        element: ProcessConfigurationElement,
    ) -> ConfigurationStructure:
        """Convert ProcessConfigurationElement to structure-only.

        Attribute values and text are discarded.
        Only element names, attribute names, and hierarchy are preserved.
        """
        # Extract attribute names only (discard values)
        attribute_names = tuple(
            name for name, _ in element.attributes
        )

        # Recursively convert children
        children = tuple(
            self._configuration_element_to_structure(child)
            for child in element.children
        )

        return ConfigurationStructure(
            element_name=element.name,
            attribute_names=attribute_names,
            children=children,
        )


class ShapeContractCatalogAggregator:
    """Aggregates shape contract extractions across multiple process definitions.

    This service takes multiple ShapeContractExtraction results and produces
    a unified ShapeContractCatalog with cross-process aggregation.

    Does NOT perform Boomi API calls.
    Does NOT require Boomi authentication.
    Does NOT retain raw Component XML.
    """

    def aggregate(
        self,
        extractions: list[ShapeContractExtraction],
    ) -> ShapeContractCatalog:
        """Aggregate multiple extractions into a unified catalog.

        Args:
            extractions: List of ShapeContractExtraction from individual processes

        Returns:
            ShapeContractCatalog with aggregated structural evidence
        """
        process_count = len(extractions)

        # Aggregate all shapes by shapetype and fingerprint
        shapetype_fingerprint_groups: dict[
            str,
            dict[str, list[ShapeVariant]]
        ] = defaultdict(lambda: defaultdict(list))

        total_shapes = 0

        for extraction in extractions:
            total_shapes += extraction.total_shapes_observed

            for shapetype_obs in extraction.shapetype_observations:
                shapetype = shapetype_obs.shapetype

                for variant in shapetype_obs.variants:
                    # Compute fingerprint from structure
                    if variant.structure is not None:
                        fingerprint = self._compute_structure_fingerprint(
                            variant.structure
                        )
                    else:
                        fingerprint = f"{shapetype}|<no-configuration>"

                    shapetype_fingerprint_groups[shapetype][fingerprint].append(
                        variant
                    )

        # Build catalog entries
        shapetype_entries: list[ShapeTypeCatalogEntry] = []

        for shapetype in sorted(shapetype_fingerprint_groups.keys()):
            fingerprint_groups = shapetype_fingerprint_groups[shapetype]

            # Sort fingerprints deterministically
            sorted_fingerprints = sorted(fingerprint_groups.keys())

            # Aggregate variants
            variant_entries: list[ShapeVariantCatalogEntry] = []
            variant_counter = 1

            for fingerprint in sorted_fingerprints:
                variants = fingerprint_groups[fingerprint]

                # Aggregate instance counts
                total_instances = sum(v.instance_count for v in variants)

                # Use first variant's structural data (all have same structure)
                first_variant = variants[0]

                # Aggregate observed cardinalities across instances
                aggregated_cardinalities = self._aggregate_cardinalities(
                    [v.observed_cardinalities for v in variants]
                )

                variant_id = f"variant-{variant_counter:03d}"
                variant_counter += 1

                variant_entries.append(
                    ShapeVariantCatalogEntry(
                        variant_id=variant_id,
                        instances_observed=total_instances,
                        structural_fingerprint=fingerprint,
                        structural_paths=first_variant.structural_paths,
                        observed_cardinalities=aggregated_cardinalities,
                    )
                )

            # Aggregate total instances for shapetype
            shapetype_total = sum(v.instances_observed for v in variant_entries)

            shapetype_entries.append(
                ShapeTypeCatalogEntry(
                    shapetype=shapetype,
                    instances_observed=shapetype_total,
                    variants=tuple(variant_entries),
                )
            )

        return ShapeContractCatalog(
            process_definitions_observed=process_count,
            shapes_observed=total_shapes,
            shapetypes=tuple(shapetype_entries),
        )

    def _compute_structure_fingerprint(
        self,
        structure: ConfigurationStructure,
    ) -> str:
        """Compute deterministic fingerprint from ConfigurationStructure."""
        parts: list[str] = []

        parts.append(f"E:{structure.element_name}")

        if structure.attribute_names:
            sorted_attrs = tuple(sorted(structure.attribute_names))
            parts.append(f"A:({','.join(sorted_attrs)})")

        if structure.children:
            child_fingerprints = tuple(
                sorted(
                    self._compute_structure_fingerprint(child)
                    for child in structure.children
                )
            )
            parts.append(f"C:({'|'.join(child_fingerprints)})")

        return ";".join(parts)

    def _aggregate_cardinalities(
        self,
        cardinality_maps: list[dict[str, dict[str, int]]],
    ) -> dict[str, dict[str, int]]:
        """Aggregate observed cardinalities across multiple instances.

        For each structural path, compute the observed min and max counts
        across all instances.

        This is observational data only, not a Boomi product contract.
        """
        result: dict[str, dict[str, int]] = {}

        for card_map in cardinality_maps:
            for path, counts in card_map.items():
                if path not in result:
                    result[path] = {"min": counts["min"], "max": counts["max"]}
                else:
                    result[path]["min"] = min(result[path]["min"], counts["min"])
                    result[path]["max"] = max(result[path]["max"], counts["max"])

        return result


class ShapeContractCatalogRenderer:
    """Renders safe human-readable reports from ShapeContractCatalog.

    The renderer emits only structural metadata - no values, identities,
    or raw XML.
    """

    def render(
        self,
        catalog: ShapeContractCatalog,
    ) -> str:
        """Render catalog as deterministic human-readable report.

        Args:
            catalog: ShapeContractCatalog to render

        Returns:
            Formatted human-readable string with structural evidence only
        """
        lines: list[str] = []

        lines.append("SHAPE CONTRACT CATALOG")
        lines.append("")
        lines.append(
            f"Process definitions observed : {catalog.process_definitions_observed}"
        )
        lines.append(f"Shapes observed              : {catalog.shapes_observed}")
        lines.append(f"Distinct shapetypes          : {len(catalog.shapetypes)}")
        lines.append("")

        for shapetype_entry in catalog.shapetypes:
            lines.append(f"SHAPETYPE: {shapetype_entry.shapetype}")
            lines.append(f"Instances observed : {shapetype_entry.instances_observed}")
            lines.append(f"Variants observed  : {len(shapetype_entry.variants)}")
            lines.append("")

            for variant in shapetype_entry.variants:
                lines.append(f"VARIANT: {variant.variant_id}")
                lines.append(f"Instances observed : {variant.instances_observed}")
                lines.append("")

                lines.append("Structural paths:")
                for path in variant.structural_paths:
                    lines.append(f"    {path}")
                lines.append("")

                if variant.observed_cardinalities:
                    lines.append("Observed cardinalities:")
                    for path, counts in sorted(variant.observed_cardinalities.items()):
                        lines.append(
                            f"    {path}: min={counts['min']}, max={counts['max']}"
                        )
                    lines.append("")

        return "\n".join(lines)
