import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-2")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

import app as app_module


class ApiValidationTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def test_rejects_missing_and_oversized_input(self):
        self.assertEqual(self.client.post("/select_agents", json={}).status_code, 400)
        response = self.client.post(
            "/select_agents", json={"user_input": "x" * (app_module.MAX_INPUT_LENGTH + 1)}
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_agents(self):
        response = self.client.post(
            "/get_responses",
            json={"user_input": "안녕", "user_id": "valid-id", "agents_used": ["Unknown"]},
        )
        self.assertEqual(response.status_code, 400)

    def test_deduplicates_agents_and_generates_response(self):
        with patch.object(app_module, "save_chat"), patch.object(
            app_module, "generate_dynamic_response", return_value="안전한 응답"
        ):
            response = self.client.post(
                "/get_responses",
                json={
                    "user_input": "안녕",
                    "user_id": "valid-id",
                    "agents_used": ["Cognitive", "Cognitive"],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.get_json()["responses"]), ["Cognitive"])

    def test_langgraph_passes_first_response_to_second_agent(self):
        observed = []

        def fake_response(agent_name, description, user_input, conversation_history,
                          last_response, last_self_response="", existing_responses=None,
                          prior_responses=None):
            observed.append((agent_name, dict(prior_responses or {})))
            return f"{agent_name} response"

        with patch.object(app_module, "save_chat"), patch.object(
            app_module, "generate_dynamic_response", side_effect=fake_response
        ), patch.object(app_module.random, "shuffle", side_effect=lambda values: None):
            response = self.client.post(
                "/get_responses",
                json={
                    "user_input": "안녕",
                    "user_id": "valid-id",
                    "agents_used": ["Emotional", "Cognitive"],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed[0], ("Emotional", {}))
        self.assertEqual(
            observed[1],
            ("Cognitive", {"Emotional": "Emotional response"}),
        )

    def test_prompt_forbids_fictional_self_disclosure(self):
        messages = app_module.build_agent_messages(
            "Emotional", app_module.agents["Emotional"], "힘들어", [], {}
        )
        system_text = "\n".join(message["content"] for message in messages)
        self.assertIn("허구적인 자기개방을 하지 마", system_text)
        self.assertNotIn("나도 느낀 적 있어", system_text)


if __name__ == "__main__":
    unittest.main()
