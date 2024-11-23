import re  

# Sample input text  
input_text = """  
Interventional Psychiatry Program – Consultation Note

{name} was seen at the Interventional Psychiatry Program at St. Michael's Hospital. The patient was assessed through Zoom video from XX to XX on Oct XX, 2024. Identity confirmed via date of birth and location. The patient’s location in Ontario was confirmed.

Informed verbal consent was obtained to communicate and provide care using virtual tools. This patient has been told about: risks related to unauthorized disclosure or interception of PHI; steps they can take to help protect their information; that care provided through video or audio communication cannot replace the need for physical examination or an in-person visit for some disorders or urgent problems; and that the patient must seek urgent care in an Emergency Department as necessary. The patient provided consent for the assessment. Limits of confidentiality discussed. The patient consented to the interview.

The scope of this clinic was described to the patient that eligibility is determined to ensure safety and efficacy of such interventional modalities.

RoC: rTMS or IV ketamine treatment.

ID: 
{name} is a {age}-year-old, single male. Lives in an apartment alone. Works in marketing. The patient reported that they don’t have any children or dependents.

Known to have: 
MDD, GAD.

HPI: 
MDD: 
Regarding the patient’s mood: 
{name} reported a long-standing feeling of having a low mood that is present most of the day, most days than not, which is mildly affected by external stimuli. Along with a loss of interest in pleasurable activities. The patient is doing them, if at all, only to pass the time. Moreover, they exhibited low energy, fatigue most of the time, and decreased interest in socializing with others, even close friends. In addition, {name} stated that they’re having low self-esteem, excessive guilt, and feelings of hopelessness. Sleep is disturbed; they reported taking quite a while to fall asleep, often over an hour, and intermittent sleep with multiple awakenings during the night. The main issue {name} is facing is difficulty in falling asleep and not waking refreshed. Similarly, appetite is also affected; the patient has been experiencing low appetite and sometimes skips meals. They reported prominent forgetfulness and distractibility, feeling that their mind is foggy a lot of the time. 
In regard to self-harm, {name} stated having some dark thoughts but clarified that they haven’t seriously considered suicide and have never acted on those thoughts.

GAD: 
{name} reported feeling anxious in social situations but has not been diagnosed with generalized anxiety. They stated feeling nervous but can’t control those worries sometimes.

PTSD:
The patient denied having experienced trauma leading to recurring distressing memories, flashbacks, or avoidance of reminders.

SUD: 
The patient denied any history of substance use, including smoking/vaping, cannabis, alcohol, stimulants, benzodiazepines, or hallucinogens.

On review of psychiatric systems, the patient denies:
Homicidal ideation
Hallucinations and delusions
Decreased need for sleep with increased energy and elevated moods.

Past History: 
Past Psychiatry History: 
Current Psychiatrist: None, primarily managing with a family doctor. 
Previous Diagnoses: Depression. 
Medications Trials: The patient has not tried any medications specifically for mental health but has discussed lifestyle changes and therapy options.

Therapy: The patient reported trying talk therapy previously.

Admissions: The patient denied any previous psychiatric admissions. 
Neurostimulation: The patient denied receiving any previous neurostimulation before. 
Psychedelic Treatments: The patient denied receiving any previous ketamine treatment before.

Past Medical History:
There is no history of: 
migraines
seizures 
head injury with loss of consciousness. 
There is no history of implanted metallic/medical devices. 
No history of tinnitus 
retinal detachment.

Current medications: None. 
Allergies: 
The patient denied any known adverse drug reactions or allergies. 
Denied any known environmental or food allergies. 
Forensic History: None. 

Family History: 
The patient denied any known mental diagnoses in the family. 
Reported a negative suicidal history in the close family. 
Denied any substance use in the family. 

Height: 5'10"
Weight: 170 pounds
MADRS=
Mental status exam: 
The patient appears to be stated age and is appropriately dressed and groomed. There are no abnormal movements noted. The patient maintained normal eye contact. Speech is normal in rhythm, rate, volume, and tone. Mood is described as "low." Affect is flat, reactive with a normal range. The thought process is linear and organized. Thought content does not demonstrate any delusions. The patient currently denies any active suicidal ideation, intent, or plan. No perceptual alterations are elicited. Cognition appears grossly normal, though no formal cognitive testing was done. Insight and judgment are intact.

Diagnoses:

Did the patient consent for experimental trials?

Impression: 

Plan: 

rTMS:
DEPRESSION: The details of our rTMS program were explained. Repetitive transcranial magnetic stimulation (rTMS) is a form of non-invasive brain stimulation that involves the delivery of repetitive electromagnetic field pulses to stimulate specific areas of the brain involved in symptoms of depression. A course of treatment involves daily treatment sessions for 4-6 weeks. We have discussed the potential benefits and risks of rTMS, including common side effects such as minor scalp sensation, lightheadedness, and headache. There is also risk of syncopal episodes or suicidal ideation. There is also a rare risk of seizure, which may occur in 1 in 10,000 individuals who receive rTMS treatment. There is a rare risk of switching to (hypo)mania. We discussed response and remission rates. We discussed medications which may reduce the efficacy of rTMS.

Ketamine: 
The details of our ketamine program were explained. IV ketamine infusions are administered twice weekly for two weeks. We have discussed limitations in existing evidence-based literature. We have discussed the potential benefits of IV ketamine treatment as well as response and remission rates. We discussed side effects, including headache, sedation, dizziness, GI upset, changes in blood pressure, blurred vision, brief dissociation, hallucination, risk of allergy, and risk of addiction. Based on current literature, the risk of addiction in this treatment context is minimal. There is also a risk of depersonalization and derealization. Side effects are short-term and generally self-limited. Our treatment program is limited to 4 infusions at this time, and maintenance treatments are not offered. Recommendations for maintenance will be provided after completion of the treatment course, and the referring physician will continue to manage the patient’s care. We explained that it is a requirement that the patient be accompanied home after each treatment, to which the patient agreed.

Plan:
Investigations – if not already completed within the last 12 months, we recommend bloodwork (CBC, lytes, lipid panel, HbA1C, fasting glucose, TSH, Vitamin B12 and Vitamin D) to rule out underlying organic causes of symptoms.
The patient agreed to be placed on the waitlist for IV Ketamine treatment. The patient will be contacted for a brief re-assessment prior to the start of treatment.
The patient should avoid alcohol and recreational substances during the course of treatment as these may interfere with the efficacy of the treatment.
For IV ketamine, we generally recommend using an oral antidepressant to maintain the benefits of ketamine therapy. MAOIs are relatively contraindicated due to the risk of hypertensive crisis. Benzodiazepines, pregabalin, gabapentin, and lamotrigine are relatively contraindicated as they may reduce the efficacy of ketamine. IV ketamine for depression has not been studied in patients taking opioid agonists, and these medications are currently a relative contraindication.
The patient may access treatment sooner through private ketamine clinics. The patient may have some coverage through insurance; otherwise, treatments are at cost.

Safety – there were no acute safety concerns at this time.

Follow-up – We have placed {name} on the waitlist for rTMS and ketamine treatment. The patient will be contacted when treatment becomes available. The patient was advised to follow up with the referring physician in 2-3 weeks.

Thank you for referring this patient to our program. Please do not hesitate to contact us if there are any concerns or questions.

Dictated by Mohammed Alhassan, Clinical fellow at IPP.
"""  

# Dictionary with replacements for labels  
replacements = {  
    "name": "John Doe",
    "age": "30",
    # Add any other replacements as needed  
}  

# Function to replace the placeholders in the text  
def replace_placeholders(text, replacements):  
    # This regex finds text in curly braces  
    pattern = r'\{(.*?)\}'  
    
    def replacement_function(match):  
        # Get the label without the braces  
        key = match.group(1)  
        # Return the corresponding value, or the original key if not found  
        return replacements.get(key, match.group(0))  
    
    # Use re.sub with the replacement_function to replace all patterns  
    return re.sub(pattern, replacement_function, text)  

# Replace placeholders in the input text  
output_text = replace_placeholders(input_text, replacements)  

# Print the updated text  
print(output_text)