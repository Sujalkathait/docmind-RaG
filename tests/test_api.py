from __future__ import annotations

"""
DocMind Second Brain — API Endpoints Test Suite
Validates FastAPI routes using IsolatedAsyncioTestCase and httpx.AsyncClient.
"""

import unittest
from httpx import ASGITransport, AsyncClient
from backend.api.main import app
from backend.database.connection import init_db


class TestSecondBrainAPI(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    async def asyncSetUp(self):
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_health_check(self):
        response = await self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["system"], "DocMind RAG + Second Brain")

    async def test_get_documents(self):
        response = await self.client.get("/api/v1/documents")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    async def test_memory_crud_api(self):
        # 1. Create memory
        payload = {
            "category": "USER_PREFERENCE",
            "key": "test_code_style",
            "value": "Write clean Python with dataclasses",
            "importance_score": 0.85,
        }
        res_post = await self.client.post("/api/v1/memory", json=payload)
        self.assertEqual(res_post.status_code, 201)
        created = res_post.json()
        mem_id = created["id"]
        self.assertEqual(created["memory_key"], "test_code_style")

        # 2. Get memories
        res_get = await self.client.get("/api/v1/memory")
        self.assertEqual(res_get.status_code, 200)
        mems = res_get.json()
        self.assertTrue(any(m["id"] == mem_id for m in mems))

        # 3. Patch memory
        res_patch = await self.client.patch(f"/api/v1/memory/{mem_id}", json={"importance_score": 0.95})
        self.assertEqual(res_patch.status_code, 200)
        self.assertEqual(res_patch.json()["importance_score"], 0.95)

        # 4. Delete memory
        res_del = await self.client.delete(f"/api/v1/memory/{mem_id}")
        self.assertEqual(res_del.status_code, 200)

    async def test_knowledge_api(self):
        # 1. Get knowledge nodes
        res_nodes = await self.client.get("/api/v1/knowledge")
        self.assertEqual(res_nodes.status_code, 200)
        self.assertIsInstance(res_nodes.json(), list)

        # 2. Get full graph
        res_graph = await self.client.get("/api/v1/knowledge/graph/full")
        self.assertEqual(res_graph.status_code, 200)
        data = res_graph.json()
        self.assertIn("nodes", data)
        self.assertIn("edges", data)

    async def test_outputs_api(self):
        res = await self.client.get("/api/v1/outputs")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    async def test_react_frontend_serving(self):
        # 1. Root route should serve React index.html
        res_root = await self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("text/html", res_root.headers.get("content-type", ""))
        self.assertIn('<div id="root"></div>', res_root.text)
        self.assertIn("DocMind RAG", res_root.text)

        # 2. SPA client-side route fallback should serve index.html
        res_spa = await self.client.get("/brain/vault")
        self.assertEqual(res_spa.status_code, 200)
        self.assertIn('<div id="root"></div>', res_spa.text)

    async def test_folders_and_models_api(self):
        # 1. Folders endpoint
        res_f = await self.client.get("/api/v1/documents/folders")
        self.assertEqual(res_f.status_code, 200)
        self.assertIn("folders", res_f.json())

        # 2. Models endpoint
        res_m = await self.client.get("/api/v1/models")
        self.assertEqual(res_m.status_code, 200)
        self.assertIn("active_model", res_m.json())

    async def test_chat_and_output_generation(self):
        # 1. Non-streaming chat endpoint
        chat_payload = {
            "message": "What is deadlock?",
            "stream": False,
        }
        res_chat = await self.client.post("/api/v1/chat", json=chat_payload)
        self.assertEqual(res_chat.status_code, 200)
        data = res_chat.json()
        self.assertIn("answer", data)
        self.assertIn("conversation_id", data)

        # 2. Flexible output generation
        out_payload = {
            "topic": "Deadlock",
            "deliverable_type": "notes",
            "folder": "General",
        }
        res_out = await self.client.post("/api/v1/outputs/generate", json=out_payload)
        self.assertEqual(res_out.status_code, 201)
        self.assertTrue(res_out.json().get("success", False))

    async def test_session_deletion_lifecycle(self):
        """Validates chat session creation, history retrieval, and clean deletion."""
        # 1. Create a session via chat query
        payload = {"message": "Test deletion session", "stream": False}
        res_create = await self.client.post("/api/v1/chat", json=payload)
        self.assertEqual(res_create.status_code, 200)
        conv_id = res_create.json()["conversation_id"]

        # 2. Verify history exists
        res_hist = await self.client.get(f"/api/v1/conversations/{conv_id}")
        self.assertEqual(res_hist.status_code, 200)
        messages = res_hist.json()
        self.assertGreater(len(messages), 0)

        # 3. Delete session via DELETE /api/v1/conversations/{conv_id}
        res_del = await self.client.delete(f"/api/v1/conversations/{conv_id}")
        self.assertEqual(res_del.status_code, 200)
        del_data = res_del.json()
        self.assertTrue(del_data["deleted"])
        self.assertEqual(del_data["session_id"], conv_id)

        # 4. Subsequent history fetch returns empty list
        res_post_del = await self.client.get(f"/api/v1/conversations/{conv_id}")
        self.assertEqual(res_post_del.status_code, 200)
        self.assertEqual(res_post_del.json(), [])

        # 5. Subsequent delete returns 404
        res_del_again = await self.client.delete(f"/api/v1/conversations/{conv_id}")
        self.assertEqual(res_del_again.status_code, 404)

    def test_solid_deliverable_strategy_factory(self):
        """Validates Strategy & Factory pattern resolution and offline generation."""
        from backend.output.strategies.factory import default_deliverable_factory
        from backend.output.strategies.study_notes import StudyNotesStrategy
        from backend.output.strategies.summary import SummaryStrategy
        from backend.output.strategies.quiz import QuizStrategy
        from backend.output.strategies.flashcards import FlashcardsStrategy

        # Factory resolution with alias normalization
        notes_strat = default_deliverable_factory.get_strategy("notes")
        self.assertIsInstance(notes_strat, StudyNotesStrategy)

        summary_strat = default_deliverable_factory.get_strategy("summary")
        self.assertIsInstance(summary_strat, SummaryStrategy)

        quiz_strat = default_deliverable_factory.get_strategy("exam")
        self.assertIsInstance(quiz_strat, QuizStrategy)

        flash_strat = default_deliverable_factory.get_strategy("flashcard")
        self.assertIsInstance(flash_strat, FlashcardsStrategy)

        # Verify offline fallback generation
        content = notes_strat.format_offline_content(
            topic="Operating Systems",
            chunks=["Processes and threads execute concurrently in OS."],
            source_labels=["OS.pdf (p. 42)"],
        )
        self.assertIn("Operating Systems", content)
        self.assertIn("OS.pdf", content)

    def test_solid_prompt_builder(self):
        """Validates fluent Builder Pattern for prompt construction."""
        from backend.orchestration.prompt_builder import ChatMLPromptBuilder

        builder = (
            ChatMLPromptBuilder()
            .set_system_instructions("You are DocMind.")
            .add_rules("Ground all answers in text.")
            .add_memories(["Prefers concise bullet points."])
            .add_evidence(["Deadlock occurs when four Coffman conditions hold."])
            .add_wiki_concepts([{"name": "Deadlock", "definition": "Mutual circular wait condition."}])
            .add_history([{"role": "user", "content": "Hello"}])
            .set_query("Explain Coffman conditions.")
        )

        prompt_str = builder.build()
        self.assertIn("<|im_start|>system", prompt_str)
        self.assertIn("Coffman conditions", prompt_str)
        self.assertIn("<|im_start|>assistant", prompt_str)

        messages = builder.build_messages()
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Hello")


if __name__ == "__main__":
    unittest.main()

