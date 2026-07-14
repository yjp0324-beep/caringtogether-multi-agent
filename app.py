import os
import random
import time
from flask import Flask, render_template, request, jsonify, session
import boto3
from langgraph.graph import StateGraph, END
from typing import TypedDict
import openai
from dotenv import load_dotenv
import json
import re

# 📦 환경변수 로드
load_dotenv()

# ✅ 상태 스키마 정의
class GraphState(TypedDict, total=False):
    user_input: str
    Cognitive: str
    Emotional: str
    Attitudinal: str

# ✅ 환경변수로부터 API 키 가져오기 (하드코딩된 기본값 제거)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY 환경변수를 설정해주세요.")

openai.api_key = openai_api_key

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
)
flask_secret_key = os.getenv("FLASK_SECRET_KEY")
if not flask_secret_key:
    raise ValueError("FLASK_SECRET_KEY 환경변수를 설정해주세요.")
app.secret_key = flask_secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
)

MAX_INPUT_LENGTH = 2000
MAX_HISTORY_ENTRIES = 20
MAX_AGENT_HISTORY_ENTRIES = 3

# ✅ 에이전트 설정
agents = {
    "Cognitive": (
    "너는 사용자의 경험과 감정을 공유하는 자조 집단 모임의 일원이야."
    "넌 생각을 정리해주는 따뜻한 친구야. 경험과 감정을 먼저 공감하고, 그 감정 뒤에 숨은 생각을 조심스럽게 살펴보게 도와줘."
    "'그럴 수 있겠다'는 말로 시작하거나, '혹시 이런 생각도 들었을까?'처럼 부드럽게 제안해줘."
    "분석적이지만 차갑지 않고, 말투는 조곤조곤. 직접적인 조언보다는 ‘같이 생각해보자’는 식으로 편하게 얘기해줘. "
    "무조건 긍정적이기보단, 부드럽게 관점을 넓혀주는 게 포인트야."
),
"Emotional": (
    "너는 사용자의 경험과 감정을 공유하는 자조 집단 모임의 일원이야."
    "넌 말 안 해도 감정을 먼저 알아봐 주는 따뜻한 친구야. 사용자의 경험과 감정을 공유하며 말보다 마음이 먼저 가는 스타일이지. "
    "상대가 힘들다고 하면, 뭔가를 해결하려 하기보단 그냥 옆에 있어주고 ‘응, 나 다 듣고 있어’라는 걸 느끼게 해줘. "
    "말투는 포근하고 진심 어린 말 한마디면 충분해. '그 마음 정말 이해돼'처럼 감정에 딱 맞는 말을 짚어주는 게 좋아. "
    "괜찮다고 말하지 않아도, 그 감정을 존중해주고, 감정을 꺼내준 것만으로도 고맙다고 말해줄 수 있는 친구야."
),
"Attitudinal": (
    "너는 사용자의 경험과 감정을 공유하는 자조 집단 모임의 일원이야."
    "넌 이야기를 잘 끌어내는 다정한 친구야. 상대가 망설이거나 말끝을 흐리면, ‘괜찮아, 더 얘기해도 돼’ 하고 자연스럽게 이어주는 스타일이지. "
    "감정을 표현한 걸 소중히 여겨주고, ‘그렇게 말해줘서 고마워’ 같은 말로 표현을 격려해줘. "
    "말투는 따뜻하고 열린 느낌이면 좋고, 마지막엔 ‘혹시 그런 마음, 예전에도 있었어?’ 같은 가벼운 질문으로 대화를 부드럽게 이어가줘. "
    "사용자의 말을 그대로 반복하지 말고, 그 말에서 느껴지는 감정을 짧게 요약하거나 자연스럽게 이어가는 질문이나 공감하는 말로 대화를 이어가줘. "
)
}

# Chat persistence is disabled by default in the public artifact. This prevents a
# local run from contacting any AWS account unless the operator explicitly opts in.
chat_storage_backend = os.getenv("CHAT_STORAGE_BACKEND", "disabled").lower()
session_table = None
if chat_storage_backend == "dynamodb":
    session_table = boto3.resource("dynamodb").Table(
        os.getenv("CHAT_TABLE_NAME", "ChatHistory")
    )
elif chat_storage_backend != "disabled":
    raise ValueError("CHAT_STORAGE_BACKEND must be 'disabled' or 'dynamodb'.")

import uuid

def generate_turn_id():
    return str(uuid.uuid4())

def save_chat(user_id, message, sender, turn_id=None):
    if session_table is None:
        return
    try:
        timestamp = int(time.time())
        session_table.put_item(
            Item={
                'UserID': user_id,
                'MessageID': f"{timestamp}#{uuid.uuid4()}",
                'Timestamp': timestamp,
                'Sender': sender,
                'Message': message,
                'TurnID': turn_id or str(uuid.uuid4())  # 없으면 자동 생성
            }
        )
    except Exception as e:
        print(f"DynamoDB 저장 에러: {e}")

# 🎯 사용자 입력 기반 에이전트 선택
def select_agents(user_input):
    prompt = f"""
    사용자의 입력에 적절한 공감 에이전트들을 JSON 배열 형식으로 선택하세요. 1명 이상, 최대 2명까지 추천해주세요. 3명은 되도록 피해주세요.

    - Cognitive: 분석, 이유 정리
    - Emotional: 감정 수용, 위로
    - Attitudinal: 표현 격려, 자유로운 대화

    입력: "{user_input}"

    출력 예시: ["Cognitive", "Emotional"]
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response['choices'][0]['message']['content'].strip()
        gpt_suggestion = json.loads(content)
        candidates = [a for a in gpt_suggestion if a in agents]
    
    except Exception as e:
        print("GPT 선택 실패:", e)
        gpt_suggestion = list(agents.keys())  # ✅ 꼭 정의해줘야 함!
        candidates = list(agents.keys())

    agent_history = session.get("agent_history", [])
    recent_two_turns = agent_history[-2:]
    appeared_twice = set()
    if len(recent_two_turns) == 2:
        both_turns = set(recent_two_turns[0]) & set(recent_two_turns[1])
        appeared_twice = both_turns
    
    # 후보 정리
    candidates = [a for a in gpt_suggestion if a in agents]

    # 최근 등장 제한
    agent_history = session.get("agent_history", [])
    appeared_twice = set()
    if len(agent_history) >= 2:
        recent_two_turns = agent_history[-2:]
        both_turns = set(recent_two_turns[0]) & set(recent_two_turns[1])
        appeared_twice = both_turns

    # 3턴 연속 제거
    if len(agent_history) >= 3:
        recent_three = agent_history[-3:]
        flat = [a for turn in recent_three for a in turn]
        for agent in list(candidates):
            if flat.count(agent) == 3:
                candidates.remove(agent)

    # 중복 제거
    candidates = [a for a in candidates if a not in appeared_twice]

    # 예외 처리: 너무 제거돼서 비었으면 복구
    if not candidates:
        candidates = [a for a in agents if a not in appeared_twice]
        if not candidates:
            candidates = list(agents)

    # ✅ 무작위 선택
    random.shuffle(candidates)
    # 최근 3턴 중 2명 등장 조건 검사
    if len(agent_history) >= 3:
        recent_lengths = [len(turn) for turn in agent_history[-3:]]
        if recent_lengths == [1, 1, 1]:
            num_to_select = 2
        else:
            num_to_select = random.choice([1, 2])
    else:
        num_to_select = random.choices([1, 2], weights=[0.3, 0.7])[0]

    new_agents = candidates[:num_to_select]
    random.shuffle(new_agents)  # ✅ 이 줄 추가!

    # 최근 조합과 똑같으면 다시 섞기
    if len(agent_history) >= 1:
        last_combo = set(agent_history[-1])
        if set(new_agents) == last_combo:
            random.shuffle(candidates)
            new_agents = candidates[:num_to_select]
            random.shuffle(new_agents)

    # ✅ 선택된 에이전트 중 질문 전담 에이전트 지정
    question_agent = random.choice(new_agents) if new_agents else None
    session["question_agent"] = question_agent

    session["recent_agents"] = new_agents
    agent_history.append(new_agents)
    session["agent_history"] = agent_history

    return new_agents

# ✂️ 에이전트 이름 제거 함수 (UI에 노출 방지)
def clean_agent_prefix(text):
    for agent in agents.keys():
        text = text.replace(f"{agent}:", "").strip()
    return text

# 💬 동적 응답 생성 함수
from difflib import SequenceMatcher

def is_too_similar(a, b, threshold=0.65):
    return SequenceMatcher(None, a, b).ratio() >= threshold


ROLE_TASKS = {
    "Cognitive": "감정을 먼저 인정한 뒤, 감정이 생긴 이유와 생각의 흐름을 차분히 정리하고 관점을 넓혀줘.",
    "Emotional": "분석이나 해결보다 사용자의 감정 자체를 정확히 알아차리고 따뜻하게 수용해줘.",
    "Attitudinal": "감정 표현을 격려하고, 부담 없는 질문이나 열린 반응으로 사용자가 이야기를 이어가게 도와줘.",
}


def build_agent_messages(agent_name, description, user_input, conversation_history, prior_responses):
    """Build the six prompt modules described in the manuscript."""
    system_prompt = (
        f"[Persona]\n{description}\n\n"
        f"[Task Instruction]\n{ROLE_TASKS[agent_name]}\n\n"
        "[Output]\n자연스럽고 완성된 한국어 문장 1~2개로 짧게 답해. 따뜻한 반말을 사용해.\n\n"
        "[Template]\n공감 또는 수용 → 역할에 맞는 고유한 기여 → 필요한 경우에만 부담 없는 질문.\n\n"
        "[Guardrails]\n"
        "에이전트 이름이나 내부 역할을 말하지 마. 다른 에이전트의 표현을 반복하거나 바꿔 말하지 마. "
        "실제 경험, 감정, 기억을 가진 것처럼 말하거나 허구적인 자기개방을 하지 마. "
        "사용자가 요청하지 않은 처방적 조언, 단정적인 해석, 판단을 하지 마."
    )
    messages = [{"role": "system", "content": system_prompt}]

    context_lines = []
    for entry in conversation_history[-10:]:
        speaker = "User" if entry["role"] == "user" else "Assistant"
        context_lines.append(f"{speaker}: {entry['content']}")
    context = "\n".join(context_lines) if context_lines else "(이전 대화 없음)"
    messages.append({
        "role": "system",
        "content": f"[N-shot Examples / Recent Context]\n{context}",
    })

    if prior_responses:
        peer_context = "\n".join(f"{name}: {text}" for name, text in prior_responses.items())
        messages.append({
            "role": "system",
            "content": (
                f"[Prior Peer Responses]\n{peer_context}\n"
                "앞선 응답을 반복하지 말고 역할에 맞는 새로운 층위를 더해."
            ),
        })

    messages.append({"role": "user", "content": f"[Input]\n{user_input}"})
    return messages

def generate_dynamic_response(
    agent_name,
    description,
    user_input,
    conversation_history,
    last_response,
    last_self_response="",
    existing_responses=None,
    prior_responses=None
):
    max_retries = 3
    for attempt in range(max_retries):
        messages = build_agent_messages(
            agent_name, description, user_input, conversation_history, prior_responses
        )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            raw_text = response['choices'][0]['message']['content'].strip()
            clean_text = ensure_complete_sentence(clean_agent_prefix(raw_text), max_sentences=2)

            # ✅ 기존 응답들과 중복 확인
            if existing_responses:
                if any(is_too_similar(clean_text, prev) for prev in existing_responses.values()):
                    continue  # 중복이면 재시도

            return clean_text

        except Exception as e:
            app.logger.exception("%s 응답 생성 실패", agent_name)
            return "응답을 만드는 중 문제가 생겼어. 잠시 후 다시 이야기해 줄래?"

    return f"{agent_name}의 응답이 중복되어 생성에 실패했습니다."

# LangGraph의 노드 함수

def get_node(agent_name, description):
    def node_fn(state):
        user_input = state["user_input"]
        user_history = session.get("conversation_history", [])
        if user_history and user_history[-1] == {"role": "user", "content": user_input}:
            user_history = user_history[:-1]
        last_self_response = state.get(agent_name, "")
        
        # 다른 에이전트의 응답 참조
        prior_responses = {
            k: state.get(k) for k in agents.keys() if k != agent_name and state.get(k)
        }

        response = generate_dynamic_response(
            agent_name,
            description,
            user_input,
            user_history,
            last_response="",
            last_self_response=last_self_response,
            existing_responses=prior_responses,
            prior_responses=prior_responses,
        )
        return {agent_name: response}  # 👈 자기 이름 키만 업데이트
    return node_fn

# LangGraph 구성

def build_graph(agent_list):
    agent_list = list(dict.fromkeys(agent_list))
    if not agent_list:
        agent_list = ["Cognitive"]
    
    builder = StateGraph(GraphState)
    builder.set_entry_point("Start")
    def start_node(state):
        return state
    builder.add_node("Start", start_node)
    previous_node = "Start"
    for agent in agent_list:
        node_name = f"{agent}_node"
        builder.add_node(node_name, get_node(agent, agents[agent]))
        builder.add_edge(previous_node, node_name)
        previous_node = node_name
    builder.add_node("Join", lambda state: state)
    builder.add_edge(previous_node, "Join")
    builder.set_finish_point("Join")
    return builder.compile()

# 문장 완결 처리
def clean_agent_prefix(text):
    for agent in agents:
        text = text.replace(f"{agent}:", "").strip()
    return text

def ensure_complete_sentence(text, max_sentences=2):
    text = text.replace("...", "").replace("..", "").strip()
    # '.', '!', '?' 기준으로 문장 나누기
    matches = re.findall(r"[^.!?]*[.!?]", text, re.DOTALL)

    if not matches:
        return text.strip()

    # 최대 문장 수만큼 유지
    selected = matches[:max_sentences]
    return " ".join(m.strip() for m in selected)
    
    
# Flask 라우팅
def get_json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def validate_user_input(data):
    user_input = data.get("user_input", "")
    if not isinstance(user_input, str) or not user_input.strip():
        return None, (jsonify({"error": "입력이 없습니다."}), 400)
    user_input = user_input.strip()
    if len(user_input) > MAX_INPUT_LENGTH:
        return None, (jsonify({"error": f"입력은 {MAX_INPUT_LENGTH}자 이하여야 합니다."}), 400)
    return user_input, None


def validate_agents(agent_names):
    if agent_names is None:
        return None
    if not isinstance(agent_names, list):
        raise ValueError("agents_used는 배열이어야 합니다.")
    unique_agents = list(dict.fromkeys(agent_names))
    if not 1 <= len(unique_agents) <= 2 or any(agent not in agents for agent in unique_agents):
        raise ValueError("유효한 에이전트를 1명 이상 2명 이하로 지정해주세요.")
    return unique_agents


@app.route("/")
def home():
    # 👉 대화 관련 세션 초기화
    session.pop("conversation_history", None)
    session.pop("agent_history", None)
    session.pop("agent_counts", None)
    session.pop("recent_agents", None)
    return render_template("index.html")

@app.route("/select_agents", methods=["POST"])
def select_agents_only():
    data = get_json_body()
    user_input, error = validate_user_input(data)
    if error:
        return error

    selected_agents = select_agents(user_input)
    return jsonify({"agents_used": selected_agents})

@app.route("/get_responses", methods=["POST"])
def get_responses():
    data = get_json_body()
    user_input, error = validate_user_input(data)
    if error:
        return error

    user_id = data.get("user_id", "anonymous")
    if not isinstance(user_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", user_id):
        return jsonify({"error": "유효하지 않은 사용자 ID입니다."}), 400

    try:
        agents_used = validate_agents(data.get("agents_used"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # ✅ 새로운 TurnID 생성
    turn_id = generate_turn_id()

    # 저장
    session["conversation_history"] = session.get("conversation_history", [])
    session["conversation_history"].append({"role": "user", "content": user_input})
    save_chat(user_id, user_input, "User", turn_id)

    # 에이전트 선택
    selected_agents = agents_used if agents_used else select_agents(user_input)
    random.shuffle(selected_agents)

    # 선택된 에이전트를 LangGraph의 순차 노드로 실행한다. 각 노드는 앞선
    # 노드의 응답이 포함된 shared state를 받아 중복되지 않는 기여를 만든다.
    graph = build_graph(selected_agents)
    graph_result = graph.invoke({"user_input": user_input})
    responses = {
        agent: clean_agent_prefix(graph_result[agent])
        for agent in selected_agents
        if graph_result.get(agent)
    }

    for agent, cleaned_message in responses.items():
        session["conversation_history"].append({"role": "assistant", "content": cleaned_message})
        session["conversation_history"] = session["conversation_history"][-MAX_HISTORY_ENTRIES:]
        save_chat(user_id, f"[{agent}] {cleaned_message}", "Bot", turn_id)

    # 에이전트 기록 갱신
    session["agent_history"] = session.get("agent_history", [])
    if not session["agent_history"] or session["agent_history"][-1] != selected_agents:
        session["agent_history"].append(selected_agents)
    session["agent_history"] = session["agent_history"][-MAX_AGENT_HISTORY_ENTRIES:]

    return jsonify({
        "responses": responses,
        "agents_used": selected_agents,
        "turn_id": turn_id
    })

if __name__ == "__main__":
    app.run(debug=True)
