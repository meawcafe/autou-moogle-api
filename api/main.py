from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from utils import generateEmailReply, classifyEmail

app = Flask(__name__)
CORS(app)

DB_path = "./mails.db"

# summarization model
# summarizer = pipeline("summarization", model="google-t5/t5-small")

def initDB():
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mails (
            id INTEGER PRIMARY KEY,
            sender TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            snippet TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            important BOOLEAN NOT NULL
        )           
    ''')
    conn.commit()
    conn.close()


@app.route('/get-mails', methods=['GET'])
def getMails():
    # get all mails from db
    try:
        conn = sqlite3.connect(DB_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mails")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        return jsonify({
            "status": {
                "message": f"Error retrieving mails: {str(e)}"
            }
        }), 500
    
    mails = []
    # gen a mail list
    for row in rows:
        mail = {
            "id": row[0],
            "sender": row[1],
            "subject": row[2],
            "body": row[3],
            "snippet": row[4],
            "time": row[5],
            "important": bool(row[6])
        }
        mails.append(mail)
    return jsonify({
        "status": {
            "message": "mails retrieved successfully"
        },
        "data": mails,
        "metadata": {
            "count": len(mails)
        }
    }), 200


@app.route('/add-mail', methods=['POST'])
def addMail():
    data = request.json
    
    sender = data.get('sender')
    subject = data.get('subject')
    body = data.get('body')

    # validate required fields
    missing_fields = []
    # if not sender:
    #     missing_fields.append("sender")
    # if not subject:
    #     missing_fields.append("subject")
    # if not body:
    #     missing_fields.append("body")
    for field in ['sender', 'subject', 'body']:
        if not data.get(field):
            missing_fields.append(field)
        
    if missing_fields:
        return jsonify({
            "status": {
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }
        }), 400
    
    # summarize the subject and body
    # summary = summarizer(text, max_new_tokens=20, max_length=20, min_length=10)
    # snippet = summary[0]['summary_text']
    snippet = 'disabled for now'
    
    # classify the email as urgent or not
    important = classifyEmail(subject, body)
    
    try:
        conn = sqlite3.connect(DB_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO mails (sender, subject, body, snippet, important)
            VALUES (?, ?, ?, ?, ?)
        ''', (sender, subject, body, snippet, important))
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({
            "status": {
                "message": f"Error adding mail: {str(e)}"
            }
        }), 500
    
    return jsonify({
        "status": {
            "message": "Mail added successfully",
            "important": important,
            "snippet": snippet
        }
    }), 201


# generate a reply to an email using AI
@app.route('/ai-reply', methods=['POST'])
def aiReply():
    data = request.json
    
    sender = data.get('sender')
    subject = data.get('subject')
    body = data.get('body')
    user_context = data.get('context', "")
    
    # validate required fields
    if not sender or not subject or not body:
        return jsonify({
            "status": {
                "message": "Missing required fields"
            }
        }), 400
    
    reply = generateEmailReply(sender, subject, body, user_context)
    
    return jsonify({
        "status": {
            "message": "Reply generated successfully",
            "user_context": user_context
        },
        "data": {
            "reply": reply
        }
    }), 200
    


if __name__ == '__main__':
    initDB()
    app.run(debug=True)