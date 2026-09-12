from __future__ import annotations

"""
DocMind Second Brain — Comprehensive Automated Test Suite
Validates SQLite schema, CRUD operations, 4-factor memory scoring,
safety distillation filters, Wiki concept mining, and context budgeting.
"""

import unittest
import os
import time

from backend.database.connection import init_db, db_session
from backend.database.crud import (
    create_document,
    get_document_by_id,
    list_documents,
    delete_document,
    add_document_chunks,
    get_chunks_for_document,
    upsert_knowledge_node,
    get_knowledge_node,
    add_knowledge_relationship,
    get_node_relationships,
    link_knowledge_source,
    get_sources_for_node,
    upsert_memory,
    get_memory,
    list_memories,
    delete_memory,
    create_output_artifact,
    list_outputs,
)
from backend.database.models import MemoryCategory
from backend.memory.scoring import (
    compute_memory_score,
    compute_recency_score,
    cosine_similarity,
    W_RELEVANCE,
    W_IMPORTANCE,
    W_RECENCY,
    W_PROJECT,
)
from backend.memory.memory_evaluator import scrub_secrets, evaluate_interaction_for_memory
from backend.memory.memory_manager import retrieve_relevant_memories
from backend.knowledge.concept_miner import extract_concepts_from_text
from backend.knowledge.relationship_builder import auto_build_cross_document_links
from backend.knowledge.graph_service import find_connected_concepts, format_wiki_context_for_prompt
from backend.orchestration.budget_controller import (
    estimate_tokens,
    trim_to_token_budget,
    allocate_context_budget,
)
from backend.orchestration.context_assembler import assemble_grounded_context


class TestSecondBrainArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    # ----------------------------------------------------
    # 1. Database & Document CRUD Tests
    # ----------------------------------------------------
    def test_document_lifecycle(self):
        doc_id = "test_doc_os_001"
        filename = "Test_OS_Book.pdf"
        doc = create_document(
            doc_id=doc_id,
            filename=filename,
            original_path="raw/pdfs/test_os.pdf",
            file_hash="abcd1234efgh5678",
            folder="Computer_Science",
            file_size=10240,
        )
        self.assertIsNotNone(doc)
        self.assertEqual(doc.id, doc_id)
        self.assertEqual(doc.folder, "Computer_Science")

        # Add chunks
        chunks = [
            "Deadlock occurs when four conditions hold: Mutual Exclusion, Hold and Wait...",
            "Process scheduling allocates CPU cycles to ready processes...",
        ]
        added = add_document_chunks(doc_id, chunks, page_numbers=[10, 11])
        self.assertEqual(added, 2)

        retrieved_chunks = get_chunks_for_document(doc_id)
        self.assertEqual(len(retrieved_chunks), 2)
        self.assertEqual(retrieved_chunks[0].page_number, 10)

        # Cleanup
        deleted = delete_document(doc_id)
        self.assertTrue(deleted)
        self.assertIsNone(get_document_by_id(doc_id))
        self.assertEqual(len(get_chunks_for_document(doc_id)), 0)

    # ----------------------------------------------------
    # 2. Wiki Knowledge Graph & Concept Mining Tests
    # ----------------------------------------------------
    def test_concept_mining_and_graph(self):
        doc_id = "test_doc_dbms_002"
        sample_text = (
            "In transaction processing, Two-Phase Locking is a concurrency control method. "
            "A deadlock occurs when transactions form a circular wait for locks."
        )

        mined = extract_concepts_from_text(sample_text, document_id=doc_id, page_number=45)
        self.assertGreaterEqual(len(mined), 1)

        # Verify concept node in DB
        node = get_knowledge_node("Deadlock")
        self.assertIsNotNone(node)
        self.assertEqual(node.category, "CONCEPT")

        # Check source grounding
        sources = get_sources_for_node(node.id)
        self.assertTrue(any(s.document_id == doc_id for s in sources))

        # Add relationship
        node_b = upsert_knowledge_node("Two-Phase Locking", "CONCEPT", "Concurrency control")
        rel_added = add_knowledge_relationship(
            source_node_id=node.id,
            target_node_id=node_b.id,
            relation_type="CAUSED_BY",
            description="2PL can induce transaction deadlocks",
        )
        self.assertTrue(rel_added)

        rels = get_node_relationships(node.id)
        self.assertGreaterEqual(len(rels), 1)

    # ----------------------------------------------------
    # 3. 4-Factor Memory Scoring Tests
    # ----------------------------------------------------
    def test_memory_scoring_formula(self):
        # Weights: 0.45 Rel + 0.25 Imp + 0.15 Rec + 0.15 Proj
        # Case 1: Perfect match across all 4 factors
        score_perfect = compute_memory_score(
            relevance_score=1.0,
            importance_score=1.0,
            last_accessed=time.time(),
            memory_project_id="PROJ_CS",
            active_project_id="PROJ_CS",
        )
        self.assertAlmostEqual(score_perfect, 1.0, delta=0.01)

        # Case 2: Zero relevance and mismatch project
        score_low = compute_memory_score(
            relevance_score=0.0,
            importance_score=0.5,
            last_accessed=time.time() - (86400 * 30),  # 30 days old
            memory_project_id="PROJ_OTHER",
            active_project_id="PROJ_CS",
        )
        # Expected: 0.45*0 + 0.25*0.5 + 0.15*(e^-1.5) + 0.15*0 = ~0.125 + 0.033 = ~0.158
        self.assertLess(score_low, 0.35)

        # Case 3: Verify weight bounds
        self.assertAlmostEqual(W_RELEVANCE + W_IMPORTANCE + W_RECENCY + W_PROJECT, 1.0)

    # ----------------------------------------------------
    # 4. Security Scrubber & Memory Distillation Tests
    # ----------------------------------------------------
    def test_security_scrubber(self):
        # Sensitive message with OpenAI key and password
        dirty = "Please use password=SuperSecret42 and token sk-abcdef12345678901234567890"
        has_secret, clean = scrub_secrets(dirty)
        self.assertTrue(has_secret)
        self.assertNotIn("SuperSecret42", clean)
        self.assertNotIn("sk-abcdef", clean)
        self.assertIn("[REDACTED_SECRET]", clean)

        # Non-sensitive message
        clean_msg = "Explain circular wait condition in operating systems."
        has_sec2, res2 = scrub_secrets(clean_msg)
        self.assertFalse(has_sec2)
        self.assertEqual(clean_msg, res2)

    def test_memory_evaluator_distillation(self):
        user_id = "test_eval_user"
        # Explicit preference
        msg = "Always explain technical concepts with C code first"
        res = evaluate_interaction_for_memory(msg, user_id=user_id)
        self.assertIsNotNone(res)
        self.assertEqual(res["category"], MemoryCategory.LEARNING_PREFERENCE)
        self.assertIn("C code first", res["value"])

        # Transient chitchat should be dropped
        chitchat_res = evaluate_interaction_for_memory("Hello there, how are you today?", user_id=user_id)
        self.assertIsNone(chitchat_res)

    # ----------------------------------------------------
    # 5. Context Assembler & Budget Controller Tests
    # ----------------------------------------------------
    def test_context_assembler(self):
        chunks = ["A deadlock is a situation where a set of processes are blocked."]
        metas = [{"source": "Operating_Systems.pdf", "page": 210, "folder": "OS"}]

        assembled = assemble_grounded_context(
            query="Explain deadlock conditions",
            raw_chunks=chunks,
            metadatas=metas,
            user_id="default_user",
        )

        self.assertIn("context", assembled)
        self.assertIn("PRIMARY DOCUMENT EVIDENCE", assembled["context"])
        self.assertIn("Operating_Systems.pdf", assembled["context"])
        self.assertIn("Operating_Systems.pdf (p. 210)", assembled["sources"])
        self.assertIn("GROUNDING INSTRUCTIONS", assembled["context"])

    def test_budget_controller(self):
        long_text = "Word " * 2000  # ~10000 chars => ~2600 tokens
        trimmed = trim_to_token_budget(long_text, max_tokens=200)
        self.assertLessEqual(estimate_tokens(trimmed), 220)

    # ----------------------------------------------------
    # 6. Deliverables Output Engine Tests
    # ----------------------------------------------------
    def test_output_artifact_creation(self):
        artifact = create_output_artifact(
            user_id="default_user",
            output_type="STUDY_NOTES",
            title="Deadlock & Synchronization Cheat Sheet",
            file_path="output/notes/test_deadlock.md",
            content_preview="# Deadlock Summary...",
        )
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.output_type, "STUDY_NOTES")

        all_outs = list_outputs(user_id="default_user")
        self.assertTrue(any(o.id == artifact.id for o in all_outs))


if __name__ == "__main__":
    unittest.main()
