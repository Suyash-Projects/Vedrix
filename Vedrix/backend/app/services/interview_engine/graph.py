from langgraph.graph import StateGraph, END
from .state import InterviewState
from .nodes import generate_question_node, evaluate_answer_node, update_memory_node

def should_continue(state: InterviewState):
    if state['current_question_index'] >= state['max_questions']:
        return "end"
    return "continue"

def create_interview_graph():
    # Initialize the graph
    workflow = StateGraph(InterviewState)
    
    # Add Nodes
    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("update_memory", update_memory_node)
    
    # Define the flow
    # Starting the interview
    workflow.set_entry_point("generate_question")
    
    # Logic: After generating a question, we wait for user answer (External to graph usually)
    # But for a fully autonomous loop (like a test or auto-interview), it looks like this:
    # generate -> evaluate -> update -> should_continue -> generate OR end
    
    workflow.add_edge("evaluate_answer", "update_memory")
    
    workflow.add_conditional_edges(
        "update_memory",
        should_continue,
        {
            "continue": "generate_question",
            "end": END
        }
    )
    
    # In a real API-driven flow, the graph will be called in segments:
    # 1. API calls graph to get first question.
    # 2. User answers, API calls graph starting at 'evaluate_answer' node.
    
    return workflow.compile()

# Compile the graph
interview_graph = create_interview_graph()
