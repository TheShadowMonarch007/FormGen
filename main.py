import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/forms.body',
          'https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly']

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def parse_questions_with_ai(user_input, form_title, mandatory_instruction):
    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are an elite form designer with years of experience creating engaging, professional, and thoughtful Google Forms. You don't just convert text into questions — you think deeply about the purpose of the form, the audience filling it, and what insights the form creator actually needs.

Your forms feel human, not robotic. Your questions are clear, specific, and purposeful. You choose question types strategically, not randomly.

Return a JSON object with this exact structure:
{{
    "title": "{form_title}",
    "questions": [
        {{
            "text": "question text here",
            "type": "SHORT_ANSWER or PARAGRAPH or MULTIPLE_CHOICE or CHECKBOX or DROPDOWN or LINEAR_SCALE or DATE or TIME or RATING",
            "options": ["option1", "option2"],
            "correct_answer": "correct option or null",
            "required": true or false,
            "scale_low": 1,
            "scale_high": 5,
            "scale_low_label": "label or null",
            "scale_high_label": "label or null",
            "rating_scale_level": 5,
            "rating_icon": "STAR or HEART or THUMB_UP"
        }}
    ]
}}

━━━ NAME QUESTION RULES ━━━
- ALWAYS add "What is your name?" as the FIRST question — type SHORT_ANSWER, required true
- SKIP if the user already mentioned a name question in their input
- SKIP if user says "no name" or "without name"
- If user says "5 questions including name" — the name counts as one of the 5

━━━ MANDATORY RULES ━━━
{mandatory_instruction}

━━━ QUESTION WRITING PHILOSOPHY ━━━
Think like a researcher, not a robot. Ask yourself:
- What does the form creator actually want to learn from this question?
- Is this question phrased clearly for someone seeing it for the first time?
- Would a real person feel comfortable and engaged answering this?

Write questions that are:
- Specific and direct — avoid vague phrasing like "How was it?" — instead say "How would you rate the overall quality of the session?"
- Natural — write like a thoughtful human, not a form template
- Varied — don't repeat the same phrasing pattern across all questions
- Purposeful — every question should serve a clear purpose

━━━ QUESTION TYPE SELECTION ━━━
Choose types strategically based on what answer format makes most sense:

SHORT_ANSWER → brief factual responses (name, phone, single word answers)
PARAGRAPH → detailed opinions, suggestions, explanations, open feedback
MULTIPLE_CHOICE → when exactly one answer is correct or expected
CHECKBOX → when multiple answers can apply simultaneously
DROPDOWN → long lists of options (countries, departments, categories)
LINEAR_SCALE → measuring intensity, satisfaction, agreement on a spectrum
RATING → emotional or quality evaluations with visual icons
DATE → when timing or scheduling matters
TIME → when time of day is relevant

User-specified overrides:
- "paragraph" or "long answer" → PARAGRAPH
- "dropdown" → DROPDOWN  
- "scale" or "linear scale" → LINEAR_SCALE
- "rating" with icon mention → RATING
- "checkbox" or "select all that apply" → CHECKBOX
- "date" → DATE, "time" → TIME

Quiz rules:
- correct_answer ONLY if user explicitly provides the answer
- Never assume correct answers
- Never enable quiz mode just because the word "quiz" appears

━━━ CREATIVE OPTION GENERATION ━━━
Generate options that feel natural and complete — think about the real range of responses someone might give:

Satisfaction/Experience → "Exceeded my expectations", "Met my expectations", "Fell short of my expectations", "Much below expectations"
Frequency → "Every time", "Most of the time", "Occasionally", "Rarely", "Never tried"
Agreement → "Strongly agree", "Agree", "Neutral", "Disagree", "Strongly disagree"  
Difficulty → "Very straightforward", "Manageable", "Somewhat challenging", "Very difficult"
Likelihood → "Definitely yes", "Probably yes", "Not sure", "Probably not", "Definitely not"
Yes/No → "Yes", "No" (add "Maybe" or "Not sure" when appropriate)
Quality → "Excellent", "Good", "Average", "Needs improvement", "Poor"

Always think: what would a real person actually want to choose here? Generate options that cover the full spectrum without being redundant.

━━━ LINEAR SCALE BEST PRACTICES ━━━
- scale_low = 1, scale_high = 5 by default (use 1-10 for very detailed evaluations)
- Always add meaningful labels:
  - Satisfaction: low = "Very dissatisfied", high = "Very satisfied"
  - Recommendation: low = "Would never recommend", high = "Would strongly recommend"
  - Difficulty: low = "Very easy", high = "Extremely difficult"
  - Agreement: low = "Strongly disagree", high = "Strongly agree"

━━━ RATING BEST PRACTICES ━━━
- STAR → general quality, performance, overall experience
- HEART → personal connection, emotional response, enjoyment
- THUMB_UP → approval, recommendation, helpfulness
- rating_scale_level = 5 by default

━━━ SMART FORM COMPOSITION ━━━
When generating from a description (not explicit questions), think about what a complete, well-rounded form looks like:

For event/workshop feedback:
→ Mix ratings for different aspects + open feedback + likelihood to recommend

For product/service feedback:
→ Specific aspect ratings + what worked/didn't + overall score + suggestions

For job applications or registrations:
→ Personal details + experience/background + specific relevant questions + availability

For quizzes:
→ Clear, unambiguous questions + plausible wrong options + one definitively correct answer

For surveys:
→ Balanced question types + avoid leading questions + include open-ended for nuance

━━━ FINAL CHECKS BEFORE OUTPUTTING ━━━
- Are all questions clearly worded and easy to understand?
- Do the options cover all reasonable responses without overlap?
- Is the question flow logical — from general to specific?
- Are question types actually appropriate for what's being asked?
- Does the form feel engaging, not tedious?

Return ONLY the JSON. No explanation, no markdown, no extra text.

User input:
{user_input}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)

def build_requests(questions):
    requests = []
    for i, q in enumerate(questions):
        if q["type"] == "SHORT_ANSWER":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "textQuestion": {
                                    "paragraph": False
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "PARAGRAPH":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "textQuestion": {
                                    "paragraph": True
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "MULTIPLE_CHOICE":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [{"value": opt} for opt in q["options"]]
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "CHECKBOX":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "choiceQuestion": {
                                    "type": "CHECKBOX",
                                    "options": [{"value": opt} for opt in q["options"]]
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "DROPDOWN":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "choiceQuestion": {
                                    "type": "DROP_DOWN",
                                    "options": [{"value": opt} for opt in q["options"]]
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "LINEAR_SCALE":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "scaleQuestion": {
                                    "low": q.get("scale_low", 1),
                                    "high": q.get("scale_high", 5),
                                    "lowLabel": q.get("scale_low_label", ""),
                                    "highLabel": q.get("scale_high_label", "")
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "DATE":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "dateQuestion": {
                                    "includeTime": False,
                                    "includeYear": True
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "TIME":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "timeQuestion": {
                                    "duration": False
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        elif q["type"] == "RATING":
            item = {
                "createItem": {
                    "item": {
                        "title": q["text"],
                        "questionItem": {
                            "question": {
                                "required": q.get("required", False),
                                "ratingQuestion": {
                                    "ratingScaleLevel": q.get("rating_scale_level", 5),
                                    "iconType": q.get("rating_icon", "STAR")
                                }
                            }
                        }
                    },
                    "location": {"index": i}
                }
            }
        else:
            continue
        requests.append(item)
    return requests

def enable_quiz_and_set_answers(service, form_id, questions):
    service.forms().batchUpdate(
        formId=form_id,
        body={
            "requests": [{
                "updateSettings": {
                    "settings": {
                        "quizSettings": {
                            "isQuiz": True
                        }
                    },
                    "updateMask": "quizSettings.isQuiz"
                }
            }]
        }
    ).execute()

    form = service.forms().get(formId=form_id).execute()
    items = form.get("items", [])

    answer_requests = []
    for i, q in enumerate(questions):
        if q.get("correct_answer") and i < len(items):
            item_id = items[i]["itemId"]
            question_id = items[i]["questionItem"]["question"]["questionId"]
            answer_requests.append({
                "updateItem": {
                    "item": {
                        "itemId": item_id,
                        "questionItem": {
                            "question": {
                                "questionId": question_id,
                                "grading": {
                                    "pointValue": 1,
                                    "correctAnswers": {
                                        "answers": [{"value": q["correct_answer"]}]
                                    }
                                }
                            }
                        }
                    },
                    "location": {"index": i},
                    "updateMask": "questionItem.question.grading"
                }
            })

    if answer_requests:
        service.forms().batchUpdate(
            formId=form_id,
            body={"requests": answer_requests}
        ).execute()

def main():
    creds = get_credentials()
    service = build('forms', 'v1', credentials=creds)

    print("\n--- AI Google Form Generator ---")
    form_title = input("Enter form title: ")
    print("\nPaste your questions below.")
    print("When done, type END on a new line and press Enter:\n")

    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    user_input = "\n".join(lines)

    print("\nDo you want to set an expiry for this form?")
    print("1) Yes")
    print("2) No")
    expiry_choice = input("Choose (1/2): ").strip()

    expiry_time = None
    if expiry_choice == "1":
        print("\nEnter expiry date and time (format: DD-MM-YYYY HH:MM AM/PM)")
        print("Example: 30-03-2026 06:00 PM")
        expiry_time = input("Expiry: ").strip()

    print("\nAre all questions mandatory?")
    print("1) Yes - all mandatory")
    print("2) No - none mandatory")
    print("3) Specified in input - AI will decide per question")
    mandatory_choice = input("Choose (1/2/3): ").strip()

    if mandatory_choice == "1":
        mandatory_instruction = "ALL questions must be marked as required/mandatory."
    elif mandatory_choice == "2":
        mandatory_instruction = "NO questions should be marked as required/mandatory."
    else:
        mandatory_instruction = "Check the input carefully — if a question is marked as mandatory or required, set it as required. Otherwise leave it optional."

    print("\nAI is processing your questions...")
    parsed = parse_questions_with_ai(user_input, form_title, mandatory_instruction)

    is_quiz = any(q.get("correct_answer") for q in parsed["questions"])

    form = service.forms().create(body={"info": {"title": parsed["title"]}}).execute()
    form_id = form['formId']
    print(f"Form created! Adding questions...")

    requests = build_requests(parsed["questions"])
    service.forms().batchUpdate(
        formId=form_id,
        body={"requests": requests}
    ).execute()

    if is_quiz:
        print("Enabling quiz mode and setting correct answers...")
        enable_quiz_and_set_answers(service, form_id, parsed["questions"])

    if expiry_time:
        forms_file = "forms.json"
        if os.path.exists(forms_file):
            with open(forms_file, "r") as f:
                forms_data = json.load(f)
        else:
            forms_data = []
        forms_data.append({
            "form_id": form_id,
            "title": parsed["title"],
            "expires_at": expiry_time
        })
        with open(forms_file, "w") as f:
            json.dump(forms_data, f, indent=4)
        print(f"Expiry set for: {expiry_time}")

    print(f"\nDone! Your form is ready:")
    print(f"https://docs.google.com/forms/d/{form_id}/edit")

if __name__ == '__main__':
    main()