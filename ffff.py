import google.generativeai as genai

# Configure API key
genai.configure(api_key="AIzaSyAxVcXI5O6fviXNRF1TZh9YnCS8rSrjoSk")  # Replace with your actual key

# Initialize the model (Gemini Pro)
model = genai.GenerativeModel('gemini-2.0-flash')

# Your unpunctuated text
text = """
to confront the mystery Miranda followed the elusive figure in the dim Corridor fleeting glimpses of determination and hidden sorrow emerged challenging her assumptions about friend and foe alike the pursuit led her to a narrow winding passage beneath the chapel in the oppressive Darkness the air grew cold and heavy and every echo of her foot steps seemed to whisper warnings of Secrets best left undisturbed in a Subterranean chamber the shadow finally halted the figure's voice emerged from the Gloom you're close to the truth but be warned some Secrets once uncovered can never be buried again the mysterious stranger introduced himself as Victor a former Confidant of Edmund his words painted a tale of coercion and betrayal a network of hidden alliances that had forced Edmund into an impossible Choice Victor detailed clandestine meetings cryptic codes and a secret society that manipulated fate from behind the scenes
"""

# Prompt for punctuation + grammar correction
prompt = f"""
Correct the following text by adding proper punctuation, capitalization, and grammar fixes. 
Return ONLY the corrected text, no additional commentary:

{text}
"""

# Generate response
response = model.generate_content(prompt)
corrected_text = response.text

print(corrected_text)