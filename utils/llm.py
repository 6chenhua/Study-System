from openai import OpenAI
import json

client = OpenAI(base_url='https://api.rcouyi.com/v1', api_key='sk-Q1mo1QMOiSl2VAXR58Eb0dA907A64c59969d323b2f7a9442')

def query_llm(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_object"
            },
            temperature=0,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during API call: {e}")
        return None


if __name__ == '__main__':
    prompt = '''Scenario Description: 
A user reads an English text aloud and the system generates the corresponding audio. We use a speech-to-text tool to transcribe the audio into text to check the accuracy of the user's reading.
However, due to the possible error of the speech recognition tool, the transcription result may be slightly different from the actual content read by the user.

Task: 
Please determine whether the following two texts are basically the same, i.e. determine whether the transcription error comes from the speech recognition tool itself rather than the user reading aloud error. Note that you need to output in json format, the json output has two fields: one is_corrected, this field has only two values, they are true and false, true means that the user read aloud correctly, but the transcription tool recognition error; false: that the user read aloud incorrectly, the inaccuracy of the transcription result is the user's own problem. The other field is reason, which indicates the explanation of the judgment result.
In addition to checking the similarity of the text, the similarity between the pronunciation of the transcribed text and that of the source text is also very important.

The original text that the user should read aloud: {{text}} 
Speech recognition transcription result: {{transcribed_text}}

Please try to check as loosely as possible, because the model used for transcription doesn't perform very well.
'''
    prompt = prompt.replace("{{text}}", "Nose").replace("{{transcribed_text}}", "No, is it?")
    res = query_llm(prompt)
    # res = json.loads(res)['is_corrected']
    print(res)