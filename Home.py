import streamlit as st
import pandas as pd
import json
import openai
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt


openai.api_key = st.secrets['OPENAI_API_KEY']
GPT_MODEL = "gpt-4o"

@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, functions=None, function_call=None, temperature=0, model=GPT_MODEL):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + openai.api_key,
    }
    json_data = {"model": model, "messages": messages, "temperature": temperature}
    if functions is not None:
        json_data.update({"functions": functions})
    if function_call is not None:
        json_data.update({"function_call": function_call})
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

def update_key():
    st.session_state.uploader_key += 1

st.title('📚 Biblio Assistant 🤓')

uploaded_file = st.file_uploader("Please upload your file with bibliographic references", type='xlsx', key=f"uploader_{st.session_state.uploader_key}")
if uploaded_file is not None:
    with st.spinner('Processing...'):
        df = pd.read_excel(uploaded_file)
        df['to_process'] = df.apply(lambda row: f"""- Title: {row.Title}
                                                - Abstract: {row.Abstract}""", axis=1)
        
        predictions = []
        for row in df.to_process:
            messages = []
            messages.append({
                'role': 'system',
                'content': """The user will give you an abstract and a title of a scientific article.
        Your job is to determine the Object of Analysis, Methodology, Scale of Analysis, Country and whether it's a Policy or an Educational Pratice.
        Finally, it should include a Classification 1, 2, 3, or 4 where: 
        1) Elabora uma revisão da literatura/mapeamento sobre determinado assunto para identificar evidências para informar políticas ou práticas educativas.
        2) Examina se determinada política ou prática é informada pela evidência científica.
        3) Analisa importância do conhecimento científico na formação ou prática de professores.
        4) Reflete sobre a avaliação de programas/iniciativas para informar políticas e práticas
        The answer should be in Portuguese and structured as a JSON.
        """})
            messages.append({
                'role': 'user',
                'content': """
        - Title: Implementation Matters: Teachers' Pedagogical Practices during the Implementation of an Interdisciplinary Curriculum in Hong Kong
        - Abstract: An interdisciplinary subject, liberal studies, was introduced as a compulsory and core subject into the New Senior Secondary Curriculum in Hong Kong in 2009 with the purpose of expanding students' knowledge base and increasing their social awareness through investigation into a variety of issues. However, transforming curricular innovations into real classroom settings and maintaining them is a complicated process. This study aimed to investigate, during its first round of implementation, teachers' pedagogical practices in 21 local schools through in-depth interviews and documentary analysis. The results reveal that the school administrators and teachers were more likely to adapt their teaching approaches and teaching materials than their teaching content and assessment. Both good practices and examination-oriented practices in the process of curriculum implementation were evident in this study. These findings contribute to our understanding of the implementation of an interdisciplinary curriculum in examination-oriented systems and inform the practitioners of school-based practices of curriculum implementation.
        """})
            messages.append({
                'role': 'assistant',
                'content': """"
        {'Objeto de Análise': 'Prática educacional',
        'Metodologia': 'Entrevistas',
        'Escala de Análise': 'Local',
        'País': 'Hong Kong',
        'Política/ prática': 'Prática',
        'Classificação': 4
        }
        """})
            messages.append({
                'role': 'user',
                'content': """
        - Title: Professional Experience: Learning from the Past to Build the Future
        - Abstract: The title of the 2014 Australian Teacher Education Association (ATEA) conference was "Teacher Education, An Audit: Building a platform for future engagement." One of the conference themes was "Professional Experience: What works? Why?" I seized upon this theme and the title of the conference as it afforded me an opportunity to do an audit of my research in professional experience over the last 25Â years. This article presents this evidence base and the messages I have taken from this evidence. I have done this in the hope that, by collating some of the insights gained from the past and the present, it will help to "build a platform for future engagement" in professional experience. In preparing this article I was asked by the Editors to reflect also on how I developed my distinctive line of inquiry and expertise in relation to the practicum across an extended period. These reflections are included. I hope they will support university-based teacher educators in enhancing their satisfaction and achievements from working in this stimulating and provocative field of study.
        """})
            messages.append({
                'role': 'assistant',
                'content': """"
        {'Objeto de Análise': 'Formação de professores',
        'Metodologia': 'Não Especificado',
        'Escala de Análise': 'Não Especificado',
        'País': 'Australia',
        'Política/ prática': 'Prática',
        'Classificação': 3
        """})

            messages.append({"role": "user", "content": row})
            chat_response = chat_completion_request(messages)
            predictions.append(chat_response.json()['choices'][0]['message']['content'])
        
        predictions_parsed = [json.loads(pred.replace("```", "").replace("json", "").replace("\n","")) for pred in predictions]
        out = pd.DataFrame(predictions_parsed)
        with pd.ExcelWriter(uploaded_file, mode='a') as writer:
            out.to_excel(writer, sheet_name='Predictions', index=False)
        
    downloaded = st.download_button(label='Download Predictions', data=uploaded_file, file_name='predictions.xlsx', on_click=update_key)
    if downloaded:
        st.toast('Thanks for using Biblio Assistant!')

