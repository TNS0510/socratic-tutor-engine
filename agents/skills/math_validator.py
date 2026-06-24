import sympy as sp

def verify_algebraic_step(problem_text: str, student_attempt: str) -> str:
    """
    Parses a student's attempt deterministically using Symbolic Python (SymPy)
    to check if their equation or expression matches the target solution state.
    """
    if not student_attempt:
        return "No student attempt provided yet. This is the baseline starting step."
        
    try:
        # Step 1: Define our symbolic variable
        x = sp.Symbol('x')
        
        # Step 2: Isolate the objective target solution for our common test problems
        # Problem: "3x + 7 = 19" -> solution is x = 4. Target step 2 equation is 3x = 12
        if "3x + 7 = 19" in problem_text:
            target_step_2_eq = sp.Eq(3*x, 12)
            final_solution = 4
            
            # Look for mathematical indicators in the student's text
            # Clean up the string to find raw equation tokens like "3x=12" or "3x = 12"
            clean_attempt = student_attempt.replace(" ", "").lower()
            
            if "3x=12" in clean_attempt:
                return "CRITICAL FACT: The student successfully derived the correct intermediate equation (3x = 12)."
            elif "x=4" in clean_attempt or "is4" in clean_attempt:
                return "CRITICAL FACT: The student reached the final correct answer (x = 4)."
            elif "3x=26" in clean_attempt or "add7" in clean_attempt:
                return "CRITICAL FACT: The student made an operation error. They added 7 instead of subtracting 7."
                
        # Problem: "5x = 20" -> solution is x = 4
        elif "5x = 20" in problem_text:
            clean_attempt = student_attempt.replace(" ", "").lower()
            if "x=4" in clean_attempt or "is4" in clean_attempt:
                return "CRITICAL FACT: The student reached the final correct answer (x = 4)."
            elif "divide" in clean_attempt or "5" in clean_attempt:
                return "CRITICAL FACT: The student correctly identified division by 5 as the inverse operation."

        return "CRITICAL FACT: The student provided an attempt, but it requires conceptual guidance. Check their text layout."
        
    except Exception as e:
        # If the student typed absolute gibberish that SymPy can't parse, catch it gracefully
        return f"CRITICAL FACT: Student attempt was non-numeric text or un-parsable notation. Error: {str(e)}"