from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PyQt6.QtCore import QObject, pyqtSignal
from dotenv import load_dotenv
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from langchain_ollama import OllamaLLM
from pydantic import BaseModel

from utils.config import setup_logger

load_dotenv()

# def load_env():
#     if getattr(sys, 'frozen', False):
#         # Get key and decrypt env file
#         key = [s[0] for s in sys._MEIPASS if s[2] == 'OPTION'][0]
#         f = Fernet(key)
        
#         env_path = os.path.join(sys._MEIPASS, 'encrypted.env')
#         with open(env_path, 'rb') as file:
#             encrypted_data = file.read()
            
#         decrypted_data = f.decrypt(encrypted_data)
#         # Load decrypted env data
#         for line in decrypted_data.decode().split('\n'):
#             if '=' in line:
#                 key, value = line.split('=', 1)
#                 os.environ[key.strip()] = value.strip()


# Instead of including .env directly, you can encrypt sensitive data
# import base64
# import os
# from cryptography.fernet import Fernet

# def encrypt_env():
#     key = Fernet.generate_key()
#     f = Fernet(key)
    
#     with open('.env', 'rb') as file:
#         env_data = file.read()
    
#     encrypted_data = f.encrypt(env_data)
    
#     with open('encrypted.env', 'wb') as file:
#         file.write(encrypted_data)
    
#     return key

# key = encrypt_env()

# a = Analysis(
#     ['src/main.py'],
#     datas=[
#         ('encrypted.env', '.'),  # Include encrypted env instead
#     ],
#     # ... rest of your config
# )

# # Add key to binary
# a.scripts += [(key, '', 'OPTION')]

class LLMService(QObject):
    response_ready = pyqtSignal(str)
    debug_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        if getattr(sys, 'frozen', False):
        # If running from bundle
            bundle_dir = os.path.dirname(sys.executable)
            resources_dir = os.path.join(os.path.dirname(bundle_dir), 'Resources')
            dotenv_path = os.path.join(resources_dir, '.env')
        else:
            # If running from source
            dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        
        self.logger = setup_logger(__name__)
        self.logger.info("AudioService initialized")

        print(f"Loading .env from: {dotenv_path}")
        print(f"Exists: {os.path.exists(dotenv_path)}")
        print(f"OPENAI_API_KEY set: {'OPENAI_API_KEY' in os.environ}")

        self.logger.info(f"Loading .env from: {dotenv_path}")
        self.logger.info(f"Exists: {os.path.exists(dotenv_path)}")
        self.logger.info(f"OPENAI_API_KEY set: {'OPENAI_API_KEY' in os.environ}")

        self.output_dir = os.path.join(os.path.expanduser('~/Documents'), 'medicalapp', 'llm_outputs')
        os.makedirs(self.output_dir, exist_ok=True)
        self.template_doc = None
        self.template_structure = None
        self.current_response_doc = None
        self.llm = None

        
        load_dotenv(dotenv_path)

    def _load_llm(self):
        # Initialize Llama model
        if self.llm is None:
            try:
                print("Loading LLM model...")
                self.debug_message.emit("Loading LLM model...")
                callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
                self.llm = OllamaLLM(
                    model="llama3.2:3b",
                    temperature=0.0,
                    repeat_penalty=1.2,
                    top_k=5,
                    num_gpu=0,
                    num_ctx=4098,
                    verbose=True
                )
                print("LLM initialization successful")
                self.debug_message.emit("LLM initialization successful")
                
            except Exception as e:
                error_msg = f"Error initializing Llama model: {str(e)}"
                print(error_msg)  # Debug print
                self.error_occurred.emit(error_msg)
                raise RuntimeError(error_msg)

    def _unload_llm(self):
        """Safely unload LLM model and clean up resources"""
        if self.llm is not None:
            try:
                print("Unloading LLM model...")
                self.debug_message.emit("Unloading LLM model...")
                # Explicitly close any open resources
                if hasattr(self.llm, 'client'):
                    self.llm.client.close()
                del self.llm
                self.llm = None
                
                # Force garbage collection
                import gc
                gc.collect()
                
                # Clean up any remaining semaphores
                try:
                    from multiprocessing import resource_tracker
                    resource_tracker.cleanup_resources()
                except Exception as e:
                    print(f"Resource cleanup warning: {e}")
                    
                print("LLM model unloaded successfully")
                self.debug_message.emit("LLM model unloaded successfully")
            except Exception as e:
                print(f"Error during model cleanup: {e}")

    def set_template(self, template_path: str):
        """Load and analyze the template document"""
        try:
            if not Path(template_path).exists():
                raise FileNotFoundError(f"Template file not found: {template_path}")
                
            self.template_doc = Document(template_path)
            
            # Validate template
            if not self.template_doc.paragraphs:
                raise ValueError("Template document is empty")
                
            return True
            
        except Exception as e:
            error_msg = f"Error loading template: {str(e)}"
            print(error_msg)  # Debug print
            self.error_occurred.emit(error_msg)
            return False

    def process_text(self, transcription: str):
        """Process the transcription with the loaded template"""
        try:
            if not transcription:
                raise ValueError("No transcription provided")
            
            if not self.template_doc:
                raise ValueError("No template loaded")

            self._load_llm()
            
            prompt = self.create_privacy_check_prompt(transcription=transcription)
            print(prompt)
            privacy_result = self.llm.invoke(prompt)

            print(privacy_result)
            self._unload_llm()
            
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
            self.debug_message.emit(updated_transcription)

            sample_note = '\n'.join([paragraph.text for paragraph in self.template_doc.paragraphs])
            import openai
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a bot that rewrites medical consultation notes using provided interview transcripts, ensuring the use of {name}, {age}, {date_of_birth}, {email}, {phone_number}."},
                    {"role": "user", "content":
                        f"""
                        Here is the original consultation note template:
                        {sample_note}

                        Please rewrite this consultation note using the following interview transcription:
                        {updated_transcription}"""
                        + """
                        Important:

                        Find all the available and possible patient's name, age, email, phone number and date of birth.

                        Replace them with {name}, {age}, {date_of_birth}, {email}, {phone_number} on new note.

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
        finally:
            self._unload_llm()

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
            results_dir = os.path.join(os.path.expanduser('~/Documents'), 'medicalapp', 'results') # Go up to project root
            os.makedirs(results_dir, exist_ok=True)

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

    def __del__(self):
        """Destructor to ensure cleanup"""
        self._unload_llm()
class PrivacyCheck(BaseModel):
    name: str
    email: str
    phone_number: str
    age: int
    date_of_birth: str
