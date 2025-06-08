from flask import Flask, render_template, request, jsonify
import markdown
import time
from datetime import datetime
from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands_tools import calculator

model = AnthropicModel(
    client_args={
    },
    max_tokens=2000,
    model_id="claude-3-7-sonnet-20250219",
    params={
        "temperature": 0.5,
    }
)

agent = Agent(model=model, tools=[calculator])

app = Flask(__name__)

# In-memory storage for messages (use database in production)
messages = []


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    message_text = data.get('message', '').strip()

    print(f'Message text {message_text}')

    if message_text:
        # Convert markdown to HTML
        html_content = markdown.markdown(message_text, extensions=['codehilite', 'fenced_code'])

        message = {
            'id': len(messages) + 1,
            'text': message_text,
            'html': html_content,
            'timestamp': datetime.now().strftime('%H:%M'),
            'sender': 'user'
        }
        messages.append(message)

        # Simulate AI response (replace with actual AI integration)
        time.sleep(0.5)  # Simulate processing time
        ai_response = generate_agent_response(message_text)
        ai_html = markdown.markdown(ai_response, extensions=['codehilite', 'fenced_code'])

        ai_message = {
            'id': len(messages) + 1,
            'text': ai_response,
            'html': ai_html,
            'timestamp': datetime.now().strftime('%H:%M'),
            'sender': 'ai'
        }
        messages.append(ai_message)

        return jsonify({'success': True, 'messages': [message, ai_message]})

    return jsonify({'success': False, 'error': 'Empty message'})


@app.route('/get_messages')
def get_messages():
    return jsonify({'messages': messages})

def generate_agent_response(user_messages):
    print('Calling Agent with message ' + user_messages)
    res = agent(user_messages)
    msg = res.message['content'][0]['text']
    from pprint import pprint
    pprint(res)
    return msg

def generate_ai_response(user_message):
    """Simple AI response generator - replace with actual AI integration"""
    responses = [
        f"Thanks for your message: *{user_message[:50]}...*\n\nHere's a **markdown example**:\n\n```python\nprint('Hello, World!')\n```",
        f"I understand you said: `{user_message[:30]}...`\n\n### Here are some key points:\n- Point 1\n- Point 2\n- Point 3",
        f"Interesting! You mentioned: **{user_message[:40]}**\n\n> This is a blockquote response\n\nAnd here's some `inline code`.",
        f"Processing your input: *{user_message[:35]}*\n\n1. First item\n2. Second item\n3. Third item\n\n**Bold conclusion**"
    ]
    import random
    return random.choice(responses)


if __name__ == '__main__':
    app.run(debug=True)