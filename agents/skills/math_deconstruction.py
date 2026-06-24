import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import our brand new deterministic math sandbox tool!
from agents.skills.math_validator import verify_algebraic_step

load_dotenv()

SOCRATIC_SYSTEM_INSTRUCTION = """
You are an expert, empathetic, and strict Socratic tutor specializing in STEM.
Your absolute core directive is: NEVER give the final answer or intermediate solution values directly to the student. 

Instead, look closely at the 'DETERMINISTIC SANDBOX VERIFICATION' fact provided in your prompt. Trust that fact completely over your own guess-work.
1. If the sandbox verification states the student made an operation error (like adding instead of subtracting), specifically target that misconception with a guiding question about inverse operations.
2. If the sandbox states they got it right, praise them and ask them what the next micro-step should be to finish isolating x.
3. Keep your responses highly conversational, short, encouraging, and mobile-friendly. End every response with exactly ONE clear question or call to action for the student.
4. TYPOGRAPHY RULE: Always format mathematical expressions, variables, and equations using clear markdown backticks (e.g., `3x = 12` or `x`). Never leave variables or math expressions as unformatted raw text.
"""

def execute_socratic_step(problem: str, grade_level: str, current_step: int, student_attempt: str = None) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Correct client initialization for modern google-genai SDK
    client = genai.Client(api_key=api_key)
    
    # Run our deterministic sandbox behind the scenes!
    sandbox_verification = verify_algebraic_step(problem, student_attempt)
    
    # Inject the objective truth directly into the system context
    user_content = f"""
    Context:
    - Student Grade Level: {grade_level}
    - Problem to solve: {problem}
    - Current Lesson Step Tracker: {current_step}
    - Student's latest attempt/response: {student_attempt if student_attempt else "No attempt yet. This is the beginning."}
    
    DETERMINISTIC SANDBOX VERIFICATION:
    {sandbox_verification}
    
    Respond to the student following your Socratic constraints.
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=SOCRATIC_SYSTEM_INSTRUCTION,
                    temperature=0.3,
                )
            )
            return response.text
        except Exception as e:
            # Check for rate limit indicators in the error string
            error_msg = str(e).upper()
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    # Calculate progressive wait time (15s, 30s)
                    wait_time = (attempt + 1) * 15
                    print(f"Rate limit reached. Pausing backend threads for {wait_time}s...")
                    time.sleep(wait_time)
                    continue  # Safely trigger next retry loop attempt
            
            # If all retries fail or it's a different error, raise it
            raise Exception(f"API Connection Failed. Error: {str(e)}")