"""Application service orchestrating corpus acquisition to catalog.

This service connects the private bounded corpus machine contract
(BoomiEngineAdapter.get_process_definition_corpus) to the generic
structural analysis pipeline:

    engine adapter
        -> raw Component XML definition strings (transient)
        -> BoomiProcessAnalyzer (per definition)
        -> BoomiShapeContractExtractor (per analysis)
        -> ShapeContractCatalogAggregator (once)
        -> ShapeContractCatalog

Responsibilities:

- Orchestration ONLY.
- No Boomi API logic lives here.
- No XML parsing beyond delegating to the analyzer.
- No fingerprint or aggregation logic.
- No rendering logic.

Raw Component XML lifetime is intentionally short: definitions are
consumed into structure-only extractions, the raw string references
are released, and no raw XML is persisted, cached, logged, or placed
in any returned model.

No deterministic physical memory zeroization is claimed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from boomi_builder.adapters.boomi_engine import (
    BoomiEngineAdapter,
)
from boomi_builder.services.boomi_process_analyzer import (
    BoomiProcessAnalyzer,
)
from boomi_builder.services.boomi_shape_contract_extractor import (
    BoomiShapeContractExtractor,
    ShapeContractCatalog,
    ShapeContractCatalogAggregator,
    ShapeContractExtraction,
)


class BoomiShapeContractCatalogError(RuntimeError):
    pass


class BoomiShapeContractCatalogService:
    """Builds a ShapeContractCatalog from the private corpus contract.

    The service fails closed: if corpus acquisition, any analysis,
    any extraction, or aggregation fails, no catalog is returned.
    Partial catalogs are never produced.
    """

    def __init__(
        self,
        engine: BoomiEngineAdapter,
        *,
        process_analyzer: BoomiProcessAnalyzer | None = None,
        extractor: BoomiShapeContractExtractor | None = None,
        aggregator: ShapeContractCatalogAggregator | None = None,
    ) -> None:
        self._engine = engine
        self._process_analyzer = (
            process_analyzer or BoomiProcessAnalyzer()
        )
        self._extractor = (
            extractor or BoomiShapeContractExtractor()
        )
        self._aggregator = (
            aggregator or ShapeContractCatalogAggregator()
        )

    def build_catalog(
        self,
        *,
        workspace: Path,
        environment: Mapping[str, str],
    ) -> ShapeContractCatalog:
        """Acquire the private corpus and build the structural catalog.

        Args:
            workspace: Active workspace directory.
            environment: Runtime environment mapping forwarded to the
                engine adapter (may carry BOOMI_* variables).

        Returns:
            ShapeContractCatalog containing structure-only evidence.

        Raises:
            Propagates adapter, analyzer, extractor and aggregator
            failures unchanged. No partial catalog is returned.
        """
        definitions = self._engine.get_process_definition_corpus(
            workspace=workspace,
            environment=environment,
        )

        # The adapter contract already guarantees a non-empty corpus.
        # This guard keeps the service fail-closed even if a different
        # engine implementation ever bypasses that contract.
        if not definitions:
            raise BoomiShapeContractCatalogError(
                "Process definition corpus was empty."
            )

        # Each definition is analyzed and extracted exactly once.
        # ProcessAnalysis and raw XML are transient and are never
        # retained in the catalog. Corpus order carries no semantic
        # meaning; deterministic normalization is owned by the
        # aggregator.
        extractions: list[ShapeContractExtraction] = [
            self._extractor.extract(
                self._process_analyzer.analyze(definition)
            )
            for definition in definitions
        ]

        # Release raw Component XML references as early as practical.
        del definitions

        return self._aggregator.aggregate(extractions)
