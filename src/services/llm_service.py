from datetime import datetime
import json
import os
from pathlib import Path
import re
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PyQt6.QtCore import QObject, pyqtSignal
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from langchain_community.llms.llamacpp import LlamaCpp
from pydantic import BaseModel

load_dotenv()
class LLMService(QObject):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.output_dir = Path("llm_outputs")
        self.output_dir.mkdir(exist_ok=True)
        self.template_doc = None
        self.template_structure = None
        self.current_response_doc = None

         # Initialize Llama model
        try:
            # Get the absolute path to the model
            current_dir = Path(__file__).parent.parent.parent  # src directory
            model_path = current_dir / "models" / "Llama-3.2-3B-Instruct-Q4_K_S.gguf"
            
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found at: {model_path}")

            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
            
            self.llm = LlamaCpp(
                model_path=str(model_path),
                n_gpu_layers=0,
                n_batch=1024,
                verbose=False,  # Set to True for debugging
                n_ctx=16348,
                max_tokens=2048,
                top_k=5,
                temperature=0.0,
                repeat_penalty=1.2,
                seed=4826
            )
            print("LLM initialization successful")
            
        except Exception as e:
            error_msg = f"Error initializing Llama model: {str(e)}"
            print(error_msg)  # Debug print
            self.error_occurred.emit(error_msg)
            raise RuntimeError(error_msg)

    def set_template(self, template_path: str):
        """Load and analyze the template document"""
        try:
            self.template_doc = Document(template_path)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Error loading template: {str(e)}")
            return False

    def process_text(self, transcription: str):
        """Process the transcription with the loaded template"""
        try:
            if not transcription:
                raise ValueError("No transcription provided")
            
            if not self.template_doc:
                raise ValueError("No template loaded")

            if not self.llm:
                raise RuntimeError("LLM chain not initialized")
            
            prompt = self.create_privacy_check_prompt(transcription=transcription)

            privacy_result = self.llm.invoke(prompt)
            print(privacy_result)
            
            updated_transcription = transcription
            
           # Step 1: Find the index of the last closing brace
            end_index = privacy_result.rfind('}') + 1
            # Step 2: Find the index of the first opening brace
            start_index = privacy_result.rfind('{')  # Search only before the last '}'

            # Step 2: Extract the JSON string  
            json_string = privacy_result[start_index:end_index]  
            print(json_string)

            # Step 3: Parse the JSON string into a Python dictionary  
            try:  
                patient_data = json.loads(json_string)  
                print(patient_data)  # Working with the extracted data  
            except json.JSONDecodeError as e:  
                print("Error decoding JSON:", e)
                self.error_occurred.emit(str(e) + '\n\nPlease try again.')
                return None


            for key, value in patient_data.items():
                # Create a regex pattern to match the exact value in the response text
                value = str(value)
                if value != "" and value != None:
                    if isinstance(value, str):  # Only replace string values
                        pattern = re.escape(value)  # Escape special characters in the value
                    updated_transcription = re.sub(pattern, f'{{{key}}}', updated_transcription)

            print(updated_transcription)

            sample_note = '\n'.join([paragraph.text for paragraph in self.template_doc.paragraphs])
            import openai
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a bot that rewrites medical consultation notes using provided interview transcripts, ensuring the use of implicit labels for personally identifiable information."},
                    {"role": "user", "content":
                        f"""
                        Here is the original consultation note:
                        {sample_note}

                        Please rewrite this consultation note using the following interview transcription:
                        {updated_transcription}"""
                        + """
                        Important:

                        Use the implicit labels in curly braces for all the available patient's personal identifiable information on new note: {name}, {age}, {date_of_birth}, {email}, {phone_number}.

                        Don't use any additional or creative labels except for {name}, {age}, {date_of_birth}, {email}, {phone_number}.

                        Do not retain any previous PII from the sample note.

                        Retain the original structure of the consultation note and do not include any explanations, comments, or additional text.
                        """
                    }
                ]
            )
            
            new_note = response.choices[0].message.content
            print(new_note)

            new_note = self.replace_pii_with_labels(new_note, patient_data)
            print(new_note)

            self.response_ready.emit(new_note)
            return new_note
                    
        except Exception as e:
            self.error_occurred.emit(str(e))
            return None

    def save_response(self, response_context: str) -> str:
        """
        Save the response to a Word document in the results directory at project root
        
        Args:
            response_context (str): The content to save
            
        Returns:
            str: Path to saved file, or None if error occurs
        """
        try:
            if not response_context:
                raise ValueError("No content to save")

            # Get project root directory and create results folder
            project_root = Path(__file__).parent.parent.parent  # Go up to project root
            results_dir = project_root / "results"
            results_dir.mkdir(exist_ok=True)

            # Create new document and add content
            doc = Document()
            doc.add_paragraph(response_context)

            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"consultation_note_{timestamp}.docx"
            output_path = results_dir / filename

            # Save the document
            doc.save(str(output_path))
            print(f"Document saved successfully at: {output_path}")
            return str(output_path)

        except Exception as e:
            error_msg = f"Error saving response: {str(e)}"
            print(error_msg)  # Debug print
            self.error_occurred.emit(error_msg)
            return None

    def create_privacy_check_prompt(self, transcription: str) -> str:

        System_prompt = """You are a bot that ONLY responds with an instance of JSON without any additional information. You have access to a JSON schema, which will determine how the JSON should be structured."""
            
        schema = json.dumps(PrivacyCheck.model_json_schema())

        task = f"""Extract the patient's personal identifiable information (PII): name, email, phone_number, age and date of birth from the following conversation transcription.
        
        {transcription}"""

        privacy_check_prompt = f"""
        <|begin_of_text|><|start_header_id|>system<|end_header_id|>

        {System_prompt}<|eot_id|>

        <|start_header_id|>user<|end_header_id|>
        Make sure to return ONLY an instance of the JSON, NOT the schema itself. Do not add any additional information.
        JSON schema:
        {schema}

        Task: {task}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
            """
        return privacy_check_prompt
    
    def replace_pii_with_labels(self, text: str, replacements: dict) -> str:
        # Convert all values to strings  
        replacements = {key: str(value) for key, value in replacements.items()}  
        # This regex finds text in curly braces
        pattern = r'\{(.*?)\}'
        def replacement_function(match):
            # Get the label without the braces
            key = match.group(1)
            # Return the corresponding value, or the original key if not found
            return replacements.get(key, match.group(0))
        
        # Use re.sub with the replacement_function to replace all patterns
        return re.sub(pattern, replacement_function, text)

class PrivacyCheck(BaseModel):
    name: str
    email: str
    phone_number: str
    age: int
    date_of_birth: str
