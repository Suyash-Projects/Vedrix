from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import InterviewState
from .nodes import generate_question_node, evaluate_answer_node, update_memory_node

def should_continue(state: InterviewState):
    if state.get('interview_complete'):
        return END
    return "continue"

def create_interview_graph():
    # Initialize the graph
    workflow = StateGraph(InterviewState)
    
    # Add Nodes
    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("update_memory", update_memory_node)
    
    # Starting the interview
    workflow.set_entry_point("generate_question")
    
    # Define the flow
    # generate -> evaluate -> update -> should_continue -> generate OR end
    workflow.add_edge("generate_question", "evaluate_answer")
    workflow.add_edge("evaluate_answer", "update_memory")
    
    workflow.add_conditional_edges(
        "update_memory",
        should_continue,
        {
            "continue": "generate_question",
            END: END
        }
    )
    
    # Compile with memory to allow pausing for user input
    # 'interrupt_before' ensures execution halts before evaluation
    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["evaluate_answer"]
    )

# Compile the graph
interview_graph = create_interview_graph()
