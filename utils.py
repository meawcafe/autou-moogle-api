from transformers import pipeline
import json, re

# text generation model
generator = pipeline(
    "text-generation",
    model="Qwen/Qwen2.5-1.5B-Instruct",
    device_map="auto",     # use gpu if available
    dtype="auto",  
)

# classification model
classifier = pipeline(model="facebook/bart-large-mnli")

def generateEmailReply(sender: str, subject: str, body: str, user_context: str = "",
                         temperature: float = 0.7,
                         max_new_tokens: int = 400) -> dict:
    """
    Generates a reply to an email using a text generation model.
    if user_context is provided, a contextual reply is generated.
    """
    
    # system prompt with user context
    SYSTEM_PROMPT = (
        "You are a professional email assistant. Respond in a clear, polite, "
        "concise, and helpful manner. If the incoming email is in English, "
        "reply in English; if it is in Portuguese, reply in Portuguese. Output "
        "EXCLUSIVELY in JSON with the following format:\n"
        "{\n  \"subject\": \"<reply subject>\",\n  \"body\": \"<reply body>\"\n}\n"
        "Do not include any comments outside the JSON."
        "If necessary, ask specific questions."
        f"Use the provided context to craft your response: {user_context}"
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content":
            f"Sender: {sender}\n"
            f"Subject: {subject}\n"
            f"Body:\n{body}\n\n"
            "Task: Draft an appropriate reply to the email above, maintaining the language of the original message."
        }
    ]

    # gen the reply
    out = generator(
        messages,
        do_sample=True,
        temperature=temperature,
        top_p=0.9,
        max_new_tokens=max_new_tokens,
        return_full_text=False,
    )

    # extract the generated text
    text = out[0]["generated_text"]

    # extract the JSON part from the generated text
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        # if the model output is not valid JSON, return a default reply
        return {
            "subject": f"Re: {subject}".strip(),
            "body": "Hello,\n\nThank you for your message. Could you please share more details?\n\nBest regards,\n"
        }

    try:
        # return the ai reply
        data = json.loads(match.group(0))
        subj = data.get("subject") or f"Re: {subject}".strip()
        body_txt = data.get("body") or "Hello,\n\nThank you for your message.\n\nBest regards,\n"
        return {"subject": subj.strip(), "body": body_txt.strip()}
    except Exception:
        # fallback in case of invalid JSON
        return {
            "subject": f"Re: {subject}".strip(),
            "body": "Hello,\n\nThank you for your message. Could you please share more details?\n\nBest regards,\n"
        }

def classifyEmail(subject: str, body: str) -> str:
    """
    Classifies the email as Productive or Unproductive.
    """
    
    # possible classification labels
    CANDIDATE_LABELS = [
        "urgent",
        "not urgent",
        "congratulations message",
        "meeting request",
        "newsletter",
        "technical support request",
        "case update",
        "system-related",
        "spam",
        "thank you message",
        "social media notification",
    ]
    
    # combine subject and body for classification
    text = f"Subject: {subject}. {body}"

    # classify the email
    result = classifier(
        text,
        CANDIDATE_LABELS,
        hypothesis_template="This email is {} and requires immediate attention.",
        multi_label=False
    )
    
    # consider only certain labels as important
    return result["labels"][0] in ["urgent", "meeting request", "newsletter", "technical support request", "case update", "system-related"]
    