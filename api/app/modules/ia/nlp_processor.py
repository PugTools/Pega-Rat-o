import logging
from typing import Any

import spacy
from spacy.language import Language

from app.modules.graphs.sync_service import GraphSyncService


logger = logging.getLogger(__name__)


class NLPProcessor:
    def __init__(self, graph_sync_service: GraphSyncService | None = None) -> None:
        self.graph_sync_service = graph_sync_service or GraphSyncService()
        self.nlp = self._load_model()

    def process_contract_text(self, contract: Any) -> list[dict[str, str]]:
        text = getattr(contract, "object", None) or getattr(contract, "description", None)
        if not text:
            return []
        entities = self.extract_entities(text)
        for entity in entities:
            self.graph_sync_service.sync_cited_entity(
                name=entity["text"],
                entity_label=entity["label"],
                source_entity_type="Contract",
                source_entity_id=str(contract.id),
            )
        return entities

    def process_expense_text(self, expense: Any) -> list[dict[str, str]]:
        text = getattr(expense, "purpose", None) or getattr(expense, "description", None)
        if not text:
            return []
        entities = self.extract_entities(text)
        for entity in entities:
            self.graph_sync_service.sync_cited_entity(
                name=entity["text"],
                entity_label=entity["label"],
                source_entity_type="Expense",
                source_entity_id=str(expense.id),
            )
        return entities

    def extract_entities(self, text: str) -> list[dict[str, str]]:
        doc = self.nlp(text)
        return [
            {"text": ent.text.strip(), "label": ent.label_}
            for ent in doc.ents
            if ent.label_ in {"ORG", "PER", "LOC"} and ent.text.strip()
        ]

    def _load_model(self) -> Language:
        try:
            return spacy.load("pt_core_news_sm")
        except OSError:
            logger.warning("spacy_pt_model_missing_using_blank_pipeline")
            return spacy.blank("pt")
