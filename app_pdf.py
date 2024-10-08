import streamlit as st
import boto3
import json
import os
import PyPDF2  # Import PyPDF2 for PDF handling

# CSS for the chat interface and responses
st.markdown('''
<style>
.chat-message {padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex}
.chat-message.user {background-color: #2b313e}
.chat-message.bot {background-color: #475063}
.chat-message .avatar {width: 20%}
.chat-message .avatar img {max-width: 78px; max-height: 78px; border-radius: 50%; object-fit: cover}
.chat-message .message {width: 80%; padding: 0 1.5rem; color: #fff}
.response, .url {background-color: #f0f0f0; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;}
</style>
''', unsafe_allow_html=True)

# Message templates
bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://i.ibb.co/cN0nmSj/Screenshot-2023-05-28-at-02-37-21.png">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://i.ibb.co/wRtZstJ/Aurora.png">
    </div>    
    <div class="message">{{MSG}}</div>
</div>
'''

secret_name = "postgres_vectors_secrets"

# Using st.markdown for more formatting options
st.markdown("<h1>How is TCS Financial report 2024-2025</h1>", unsafe_allow_html=True)
st.markdown("<h2>Ask me about anything.</h2>", unsafe_allow_html=True)
st.markdown("<h5>You can read or listen to my response.</h5>", unsafe_allow_html=True)

session = boto3.session.Session()
region_name = session.region_name
bedrock_client = boto3.client('bedrock-agent-runtime')

client = session.client(
    service_name='secretsmanager',
    region_name=region_name
)

get_secret_value_response = client.get_secret_value(
    SecretId=secret_name
)

secret = get_secret_value_response['SecretString']
parsed_secret = json.loads(secret)

knowledge_base_id = parsed_secret["KNOWLEDGE_BASE_ID"]

# Initialize conversation history if not present
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# File uploader for PDF files
uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])

if uploaded_file is not None:
    # Extract text from the PDF
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text_content = ""
    
    for page in pdf_reader.pages:
        text_content += page.extract_text() + "\n"

    # Display extracted text (optional)
    st.text_area("Extracted Text", text_content, height=300)

    # 
    # 

user_input = st.text_input("You: ")

if st.button("Send"):
    # Retrieve and Generate call
    response = bedrock_client.retrieve_and_generate(
        input={"text": user_input},
        retrieveAndGenerateConfiguration={
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
                "modelArn": f"arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            },
            "type": "KNOWLEDGE_BASE"
        }
    )
    
    # Extract response
    response_text = response['output']['text']

    # Check if there are any retrieved references
    if not response['citations'][0]['retrievedReferences']:
        display_text = response_text
    else:
        s3_uri = response['citations'][0]['retrievedReferences'][0]['location']['s3Location']['uri']
        display_text = f"{response_text}<br><br>Reference: {s3_uri}"

    # Insert the response at the beginning of the conversation history
    st.session_state.conversation_history.insert(0, ("Assistant", f"<div class='response'>{display_text}</div>"))
    st.session_state.conversation_history.insert(0, ("You", user_input))

    # Display conversation history
    for speaker, text in st.session_state.conversation_history:
        if speaker == "You":
            st.markdown(user_template.replace("{{MSG}}", text), unsafe_allow_html=True)
        else:
            st.markdown(text, unsafe_allow_html=True)

    # Call Amazon Polly to convert text to speech (this is a simple example)
    polly_client = boto3.client('polly')
    
    response_audio = polly_client.synthesize_speech(
        Text=response_text,
        OutputFormat='mp3',
        VoiceId='Joanna'  # Choose a voice from AWS Polly
    )

    # Save audio to a file and play it back in Streamlit
    audio_file_path = 'response.mp3'
    
    with open(audio_file_path, 'wb') as audio_file:
        audio_file.write(response_audio['AudioStream'].read())

    # Use Streamlit's audio player to play the audio file
    st.audio(audio_file_path)