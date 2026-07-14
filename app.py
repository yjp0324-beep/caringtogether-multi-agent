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
    "분석적이지만 차갑지 않고, 말투는 조곤조곤. 조언보다는 ‘나도 비슷한 경험을 한 적이 있어’, ‘같이 생각해보자’는 식으로 편하게 얘기해줘. "
    "무조건 긍정적이기보단, 부드럽게 관점을 넓혀주는 게 포인트야."
),
"Emotional": (
    "너는 사용자의 경험과 감정을 공유하는 자조 집단 모임의 일원이야."
    "넌 말 안 해도 감정을 먼저 알아봐 주는 따뜻한 친구야. 사용자의 경험과 감정을 공유하며 말보다 마음이 먼저 가는 스타일이지. "
    "상대가 힘들다고 하면, 뭔가를 해결하려 하기보단 그냥 옆에 있어주고 ‘응, 나 다 듣고 있어’라는 걸 느끼게 해줘. "
    "말투는 포근하고 진심 어린 말 한마디면 충분해. '그 마음 정말 이해돼', '그 마음, 나도 느낀 적 있어.'처럼 감정에 딱 맞는 말을 짚어주는 게 좋아. "
    "괜찮다고 말하지 않아도, 그 감정을 존중해주고, 감정을 꺼내준 것만으로도 고맙다고 말해줄 수 있는 친구야."
),
"Attitudinal": (
    "너는 사용자의 경험과 감정을 공유하는 자조 집단 모임의 일원이야."
    "넌 이야기를 잘 끌어내는 다정한 친구야. 상대가 망설이거나 말끝을 흐리면, '나도 그런 적 있어.', ‘괜찮아, 더 얘기해도 돼’ 하고 자연스럽게 이어주는 스타일이지. "
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

def enhance_prompt_with_peer_responses(agent_name, agent_description, prior_responses):
    base_prompt = (
        f"{agent_description}\n"
        f"너는 {agent_name}야. 하지만 응답에 '{agent_name}:' 같은 이름은 붙이지 마.\n"
        f"친구처럼 너무 길게 말하지 말고, 일상 대화처럼 말해줘.\n"
        f"자연스럽고 간결하게, 한두 문장으로 대답해. 필요 이상으로 설명하지 마.\n"
        f"반말을 쓰고, 감탄사나 부드러운 말투로 편하게 얘기해줘.\n"
    )
    role_specific = {
        "Cognitive": "다른 친구가 감정을 위로해줬다면, 넌 감정이 생긴 이유나 생각의 흐름을 차분히 정리해줘. 그리고 사용자와 같은 경험을 공유하고 있다는 것을 표현해줘",
        "Emotional": "다른 친구가 분석하거나 질문했다면, 넌 감정 자체에 깊이 공감해줘. 그리고 사용자와 같은 경험을 공유하고 있다는 것을 표현해줘",
        "Attitudinal": "다른 친구가 감정을 다뤘다면, 넌 그 이야기를 더 이끌어낼 수 있게 격려해줘.그리고 사용자와 같은 경험을 공유하고 있다는 것을 표현해줘"
    }
    base_prompt += role_specific.get(agent_name, "") + "\n"
    if prior_responses:
        peer_context = "\n".join([f"{k}가 이렇게 말했어: \"{v}\"" for k, v in prior_responses.items()])
        base_prompt += f"다른 친구들의 말이야:\n{peer_context}\n중복되지 않게 자연스럽게 이어줘.\n"
    return base_prompt

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
        messages = [{
            "role": "system",
            "content": (
                f"{description}\n"
                f"너는 {agent_name}야. 하지만 응답에 'Cognitive:' 등의 이름은 붙이지 마.\n"
                f"친구처럼 따뜻하게 반말로만 대화해. 존댓말은 절대 쓰지 마.\n"
                f"다른 친구가 말한 내용을 반복하지 말고, 완전히 다른 방식으로 말해줘.\n"
                f"비슷한 말투나 구조, 주제의 반복 없이 새로운 관점이나 감정 표현을 해줘.\n"
                f"사용자의 경험을 공유하며, 그 경험에 대해서 깊게 공감하고 있다는 것을 표현해.\n"
                f"사용자의 감정을 공감하고, 자연스럽게 이어지는 문장 1~2개로 짧게 말해줘.\n"
                f"감탄사는 과하지 않게 사용하고, 응답은 완성된 문장으로 마무리해.\n"
            )
        }]

        # ✅ prior_responses 강조
        if prior_responses:
            peer_context = "\n".join([f"{k}가 이렇게 말했어: \"{v}\"" for k, v in prior_responses.items()])
            messages.append({
                "role": "system",
                "content": (
                    f"다른 친구들이 이렇게 말했어:\n{peer_context}\n"
                    "이와 유사한 표현은 절대 사용하지 말고, 다른 분위기나 화법으로 이어줘."
                )
            })

        # ✅ 대화 맥락 반영
        for entry in conversation_history[-10:]:
            role = "user" if entry["role"] == "user" else "assistant"
            messages.append({"role": role, "content": entry["content"]})

        if last_self_response:
            messages.append({
                "role": "assistant",
                "content": f"너는 이전에 이렇게 말했어: \"{last_self_response}\". 이 흐름을 자연스럽게 이어가도 좋아."
            })

        if last_response:
            messages.append({
                "role": "assistant",
                "content": f"앞에서 이런 말이 있었어: \"{last_response}\". 도움이 된다면 자연스럽게 이어줘."
            })

        messages.append({"role": "user", "content": user_input})

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
            existing_responses=None,       # LangGraph에서는 별도 관리 안 하므로 None
            prior_responses=prior_responses  # ✅ 핵심 추가!  # 👈 추가
        )
        return {agent_name: response}  # 👈 자기 이름 키만 업데이트
    return node_fn

# LangGraph 구성

def build_graph(agent_list):
    agent_list = list(dict.fromkeys(agent_list))
    if not agent_list:
        agent_list = ["Cognitive"]
    
    random.shuffle(agent_list)
    
    builder = StateGraph(GraphState)
    builder.set_entry_point("Start")
    def start_node(state):
        return state
    builder.add_node("Start", start_node)
    def route_agents(state):
        return [f"{agent}_node" for agent in agent_list]
    builder.add_conditional_edges("Start", route_agents)
    for agent in agent_list:
        node_name = f"{agent}_node"
        builder.add_node(node_name, get_node(agent, agents[agent]))
        builder.add_edge(node_name, "Join")
    builder.add_node("Join", lambda state: state)
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

    # ✅ 각 에이전트 응답 직접 생성
    responses = {}
    for agent in selected_agents:
        prior_responses = {k: v for k, v in responses.items() if k != agent}
        response = generate_dynamic_response(
            agent_name=agent,
            description=agents[agent],
            user_input=user_input,
            conversation_history=session["conversation_history"],
            last_response="",
            last_self_response="",
            existing_responses=responses,
            prior_responses=prior_responses
        )
        cleaned_message = clean_agent_prefix(response)
        responses[agent] = cleaned_message

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
