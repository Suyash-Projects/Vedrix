from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import InterviewState
from .nodes import generate_question_node, evaluate_answer_node, update_memory_node


def should_continue(state: InterviewState):
    if state.get('interview_complete'):
        return END
    return "continue"


def create_interview_graph():
    workflow = StateGraph(InterviewState)

    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("update_memory", update_memory_node)

    workflow.set_entry_point("generate_question")
    workflow.add_edge("generate_question", "evaluate_answer")
    workflow.add_edge("evaluate_answer", "update_memory")

    workflow.add_conditional_edges(
        "update_memory",
        should_continue,
        {"continue": "generate_question", END: END}
    )

    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["evaluate_answer"]
    )


interview_graph = create_interview_graph()
