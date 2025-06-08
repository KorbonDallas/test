from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time
import threading
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Configure SocketIO with better settings for stability
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Store active sessions
active_sessions = {}


@app.route('/')
def index():
    return render_template('chat.html')


def simulate_streaming_response(message, session_id, client_sid):
    """Simulate a streaming response from an AI/chatbot with proper session handling"""
    try:
        # Check if session is still active
        if session_id not in active_sessions:
            print(f"Session {session_id} no longer active, stopping stream")
            return

        # Example responses with markdown
        responses = {
            "hello": "Hello! 👋 Welcome to our **modern chat interface**. How can I help you today?",
            "markdown": """Here's an example of **markdown rendering**:

## Features
- **Bold text** and *italic text*
- `Inline code` and code blocks
- Lists and formatting
- Links: [GitHub](https://github.com)

```python
def hello_world():
    print("Hello from the chat!")
```

> This is a blockquote with some important information.
""",
            "default": f"""Thanks for your message: "*{message}*"

I'm a **streaming chat bot** that can render:
- ✅ **Markdown formatting**
- ✅ `Code snippets`
- ✅ Lists and quotes
- ✅ Real-time streaming

### How it works:
1. You send a message via WebSocket
2. I process it on the server
3. Stream back the response in chunks
4. The UI renders markdown in real-time

Try typing "markdown" to see more examples!
"""
        }

        # Select response based on message content
        if "hello" in message.lower():
            response_text = responses["hello"]
        elif "markdown" in message.lower():
            response_text = responses["markdown"]
        else:
            response_text = responses["default"]

        # Stream the response word by word with realistic timing
        words = response_text.split()
        current_text = ""

        for i, word in enumerate(words):
            # Check if session is still active before each emit
            if session_id not in active_sessions:
                print(f"Session {session_id} disconnected during streaming")
                return

            current_text += word + " "

            # Emit the partial response to specific client using room
            socketio.emit('message_chunk', {
                'text': current_text.strip(),
                'is_complete': False,
                'session_id': session_id
            }, to=client_sid)

            # Vary the delay for more realistic streaming
            if word.endswith('.') or word.endswith('!') or word.endswith('?'):
                time.sleep(0.15)  # Longer pause after sentences
            else:
                time.sleep(0.08)  # Normal word delay

        # Send final complete message if session still active
        if session_id in active_sessions:
            socketio.emit('message_chunk', {
                'text': current_text.strip(),
                'is_complete': True,
                'session_id': session_id
            }, to=client_sid)

    except Exception as e:
        print(f"Error in streaming response: {e}")
        # Send error message to client
        socketio.emit('message_chunk', {
            'text': "Sorry, there was an error processing your message.",
            'is_complete': True,
            'session_id': session_id,
            'error': True
        }, to=client_sid)


@socketio.on('send_message')
def handle_message(data):
    try:
        message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))
        client_sid = request.sid  # Get the client session ID within request context

        if not message:
            emit('error', {'msg': 'Empty message received'})
            return

        print(f"Received message from {session_id} (client: {client_sid}): {message}")

        # Update session tracking
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                'sid': client_sid,
                'connected_at': time.time()
            }

        # Echo the user message immediately
        emit('user_message', {
            'message': message,
            'session_id': session_id
        })

        # Start streaming response in a separate thread with proper session tracking
        def stream_wrapper():
            simulate_streaming_response(message, session_id, client_sid)

        thread = threading.Thread(target=stream_wrapper, daemon=True)
        thread.start()

    except Exception as e:
        print(f"Error handling message: {e}")
        emit('error', {'msg': 'Error processing message'})


@socketio.on('connect')
def handle_connect():
    try:
        client_sid = request.sid  # Get client session ID within request context
        session_id = str(uuid.uuid4())

        active_sessions[session_id] = {
            'sid': client_sid,
            'connected_at': time.time()
        }

        print(f'Client connected: {client_sid} with session {session_id}')
        emit('status', {
            'msg': 'Connected to chat server',
            'session_id': session_id
        })

    except Exception as e:
        print(f"Error on connect: {e}")


@socketio.on('disconnect')
def handle_disconnect():
    try:
        client_sid = request.sid  # Get client session ID within request context

        # Remove session from active sessions
        session_to_remove = None
        for session_id, session_data in active_sessions.items():
            if session_data['sid'] == client_sid:
                session_to_remove = session_id
                break

        if session_to_remove:
            del active_sessions[session_to_remove]
            print(f'Client disconnected: {client_sid}, removed session {session_to_remove}')
        else:
            print(f'Client disconnected: {client_sid} (no session found)')

    except Exception as e:
        print(f"Error on disconnect: {e}")


@socketio.on('ping')
def handle_ping():
    """Handle ping requests to keep connection alive"""
    emit('pong')


# Clean up old sessions periodically
def cleanup_sessions():
    """Remove sessions older than 1 hour"""
    current_time = time.time()
    sessions_to_remove = []

    for session_id, session_data in active_sessions.items():
        if current_time - session_data['connected_at'] > 3600:  # 1 hour
            sessions_to_remove.append(session_id)

    for session_id in sessions_to_remove:
        del active_sessions[session_id]
        print(f"Cleaned up old session: {session_id}")


# Start cleanup thread
cleanup_thread = threading.Thread(target=lambda: None, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    print("Visit http://localhost:5000 to access the chat interface")
    socketio.run(
        app,
        debug=True,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True
    )