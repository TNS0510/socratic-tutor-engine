import os
import time
import google.generativeai as genai
from google.generativeai import types
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
    
    # Correct configuration initialization for 'google-generativeai'
    genai.configure(api_key=api_key)
    
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
          # Set this back to gemini-1.5-flash
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                system_instruction=SOCRATIC_SYSTEM_INSTRUCTION
            )
            
            # Execute generation with generation parameters
            response = model.generate_content(
                user_content,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                )
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "503" in str(e):
                if attempt < max_retries - 1:
                    print(f"API Rate Limited. Retrying... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(10)
                    continue
            raise Exception(f"API Connection Failed. Error: {str(e)}")