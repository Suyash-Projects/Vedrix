from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import InterviewState
from .nodes import (
    generate_question_node, 
    evaluate_answer_node, 
    evaluate_code_node, 
    update_memory_node,
    empathy_analyzer_node,
    skeptic_evaluation_node,
    pragmatist_evaluation_node,
    bias_auditor_node,
    consensus_synthesizer_node,
    code_copilot_node,
    debate_router_node,
)
from .supervisor_node import supervisor_node  # Phase 1B: AI Supervisor (replaces advisor_monitor)
from .planner_node import planner_node
from .sentiment_node import sentiment_node
from .qa_node import qa_agent_node


def should_continue(state: InterviewState):
    if state.get('interview_complete', False):
        return END
    return "continue"


def route_after_input(state: InterviewState):
    if state.get("copilot_request_pending"):
        return "code_copilot"
    return "debate"


def route_after_qa(state: InterviewState):
    """Route after QA agent evaluation.
    
    - If approved: proceed to sentiment analysis
    - If regenerate: loop back to generate_question (up to 3 times)
    - If regeneration count exceeded (escalated): proceed to sentiment
    """
    if state.get("approved", False):
        return "sentiment"
    if state.get("regenerate", False):
        return "generate_question"
    # Default: proceed to sentiment (safety fallback)
    return "sentiment"


def create_interview_graph():
    workflow = StateGraph(InterviewState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("qa_agent", qa_agent_node)
    workflow.add_node("sentiment", sentiment_node)
    workflow.add_node("empathy_analyzer", empathy_analyzer_node)
    workflow.add_node("code_copilot", code_copilot_node)
    workflow.add_node("debate_router", debate_router_node)
    workflow.add_node("skeptic_evaluation", skeptic_evaluation_node)
    workflow.add_node("pragmatist_evaluation", pragmatist_evaluation_node)
    workflow.add_node("bias_auditor", bias_auditor_node)
    workflow.add_node("consensus_synthesizer", consensus_synthesizer_node)
    workflow.add_node("update_memory", update_memory_node)
    workflow.add_node("supervisor", supervisor_node)  # Phase 1B: AI Supervisor

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "generate_question")
    
    # From generate_question, proceed to QA agent for bias/relevance check
    workflow.add_edge("generate_question", "qa_agent")
    
    # QA agent routes: approved → sentiment, regenerate → generate_question
    workflow.add_conditional_edges(
        "qa_agent",
        route_after_qa,
        {
            "sentiment": "sentiment",
            "generate_question": "generate_question",
        }
    )
    
    # Sentiment node proceeds to empathy_analyzer
    workflow.add_edge("sentiment", "empathy_analyzer")
    
    # After empathy analyzer, either trigger co-pilot or run evaluation debate
    workflow.add_conditional_edges(
        "empathy_analyzer",
        route_after_input,
        {
            "code_copilot": "code_copilot",
            "debate": "debate_router"
        }
    )
    
    # Loop co-pilot back to sentiment so it halts again awaiting candidate action
    workflow.add_edge("code_copilot", "sentiment")
    
    # debate_router splits to parallel debate nodes
    workflow.add_edge("debate_router", "skeptic_evaluation")
    workflow.add_edge("debate_router", "pragmatist_evaluation")
    workflow.add_edge("debate_router", "bias_auditor")
    
    # Parallel debate nodes join at the synthesizer
    workflow.add_edge("skeptic_evaluation", "consensus_synthesizer")
    workflow.add_edge("pragmatist_evaluation", "consensus_synthesizer")
    workflow.add_edge("bias_auditor", "consensus_synthesizer")
    
    # Synthesizer updates memory and triggers supervisor
    workflow.add_edge("consensus_synthesizer", "update_memory")
    workflow.add_edge("update_memory", "supervisor")  # Supervisor runs after memory
 
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {"continue": "generate_question", END: END}
    )
 
    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["sentiment"]
    )


interview_graph = create_interview_graph()
