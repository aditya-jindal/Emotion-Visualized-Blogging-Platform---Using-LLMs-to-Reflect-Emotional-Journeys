import re
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sqlite3

from flask import Flask, request, render_template, redirect, url_for, session, flash
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain

# Initialize Flask application
app = Flask(__name__)
app.secret_key = "42"  

# Set up database
def init_db():
    conn = sqlite3.connect('diary3.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        entry_date DATE NOT NULL,
        content TEXT NOT NULL,
        sentiment TEXT,
        sentiment_score REAL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weekly_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        week_start DATE NOT NULL,
        week_end DATE NOT NULL,
        overall_sentiment TEXT,
        key_events TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize LangChain models - Updated to use langchain_groq
def init_llm(temperature=0.7):
    # Get Groq API key from environment
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    # Initialize Groq LLM using ChatGroq
    return ChatGroq(
        api_key=groq_api_key,
        model="llama3-70b-8192",  # Using Llama3 model
        temperature=temperature
    )

# Daily sentiment analysis LLM
def create_daily_sentiment_analyzer():
    llm = init_llm(temperature=0.3)  # Lower temperature for more consistent analysis
    
    daily_prompt = PromptTemplate(
        input_variables=["entry"],
        template="""
        Analyze the sentiment of the following diary entry. Identify the most prominent emotions 
        expressed and provide a brief analysis. Rate the overall sentiment on a scale from -1.0 
        (extremely negative) to 1.0 (extremely positive).
        
        Diary Entry:
        {entry}
        
        Format your response as a JSON object with the following fields:
        - prominent_emotion: The most dominant emotion expressed
        - sentiment_score: A float between -1.0 and 1.0
        - brief_analysis: A one-sentence summary of the emotional state
        """
    )
    
    return LLMChain(llm=llm, prompt=daily_prompt, output_key="sentiment_analysis")

# Weekly summary and analysis LLM
def create_weekly_analyzer():
    llm = init_llm(temperature=0.5)
    
    weekly_prompt = PromptTemplate(
        input_variables=["entries"],
        template="""
        Review the following diary entries from the past week. Analyze the overall emotional 
        trajectory, identify any significant events, and determine the dominant emotional themes.
        
        Diary Entries:
        {entries}
        
        Format your response as a JSON object with the following fields:
        - overall_sentiment: The general emotional state for the week
        - emotional_trajectory: How emotions changed throughout the week
        - key_events: List of significant events that appeared to impact emotions
        - recommendations: Gentle suggestions based on the emotional patterns
        """
    )
    
    return LLMChain(llm=llm, prompt=weekly_prompt, output_key="weekly_analysis")

# Database functions
def add_entry(user_id, content):
    conn = sqlite3.connect('diary3.db')
    cursor = conn.cursor()
    
    # Get current date
    entry_date = datetime.now().strftime('%Y-%m-%d')
    
    # Add entry to database (without sentiment initially)
    cursor.execute(
        'INSERT INTO entries (user_id, entry_date, content) VALUES (?, ?, ?)',
        (user_id, entry_date, content)
    )
    entry_id = cursor.lastrowid
    conn.commit()
    
    def extract_json_block(text):
        match = re.search(r'\{.*?\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None
    
    # Analyze sentiment
    daily_analyzer = create_daily_sentiment_analyzer()
    result = daily_analyzer.run(entry=content)

    sentiment_data = extract_json_block(result)
    if sentiment_data:
        sentiment = sentiment_data.get('prominent_emotion', 'neutral')
        try:
            sentiment_score = float(sentiment_data.get('sentiment_score', 0.0))
        except (ValueError, TypeError):
            sentiment_score = 0.0
    else:
        sentiment = 'neutral'
        sentiment_score = 0.0
        print(f"Error parsing sentiment result: {result}")

    # Save the sentiment analysis into the DB
    cursor.execute(
        'UPDATE entries SET sentiment = ?, sentiment_score = ? WHERE id = ?',
        (sentiment, sentiment_score, entry_id)
    )
    conn.commit()
    conn.close()
    return result

def get_entries_for_week(user_id):
    conn = sqlite3.connect('diary3.db')
    cursor = conn.cursor()
    
    # Get entries from the past 7 days
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    cursor.execute(
        '''SELECT entry_date, content, sentiment, sentiment_score 
           FROM entries 
           WHERE user_id = ? AND entry_date BETWEEN ? AND ?
           ORDER BY entry_date''',
        (user_id, week_ago, today)
    )
    
    entries = cursor.fetchall()
    conn.close()
    
    # Format entries for the LLM
    formatted_entries = []
    for date, content, sentiment, score in entries:
        formatted_entries.append(f"Date: {date}\nEntry: {content}\n")
    
    return "\n".join(formatted_entries)


def extract_json_block(text):
    """Extract JSON from LLM response text, handling various formats."""
    # Try to find JSON block using regex
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}\nText: {match.group(0)}")
            
            # Try with additional cleanup - sometimes LLMs add extra quotes or formatting
            cleaned_text = match.group(0).replace('\\"', '"').replace("\'", '"')
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass
    
    # Last resort - check if the entire text is JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"Failed to extract JSON from: {text[:100]}...")
        return None

def generate_weekly_summary(user_id):
    # Get entries from the past week
    entries_text = get_entries_for_week(user_id)
    if not entries_text.strip():
        return {
            "overall_sentiment": "No entries this week", 
            "key_events": [],
            "emotional_trajectory": "No data available",
            "recommendations": "Consider writing daily entries to track your emotions"
        }
    
    print("Generating weekly analysis...")
    
    # Run weekly analysis
    try:
        weekly_analyzer = create_weekly_analyzer()
        result = weekly_analyzer.run(entries=entries_text)
        print(f"Weekly analysis raw result: {result[:200]}...")  # Print just the start for debugging
        
        # Extract and parse the JSON block
        weekly_data = extract_json_block(result)
        if not weekly_data:
            print(f"Error parsing weekly analysis result - falling back to structured extraction")
            # Fallback logic - try to extract key fields manually
            overall_sentiment = "neutral"
            key_events = []
            
            if "overall_sentiment" in result:
                match = re.search(r'"overall_sentiment":\s*"([^"]+)"', result)
                if match:
                    overall_sentiment = match.group(1)
            
            if "key_events" in result:
                # Try to extract a list of events
                events_text = re.search(r'"key_events":\s*(\[.*?\])', result, re.DOTALL)
                if events_text:
                    try:
                        key_events = json.loads(events_text.group(1))
                    except:
                        key_events = ["Error parsing events"]
            
            weekly_data = {
                "overall_sentiment": overall_sentiment,
                "key_events": key_events,
                "emotional_trajectory": "Unable to determine",
                "recommendations": "Continue journaling to track your emotional patterns"
            }
    except Exception as e:
        print(f"Error generating weekly summary: {str(e)}")
        return {
            "overall_sentiment": "Error analyzing entries", 
            "key_events": ["There was a problem analyzing your entries this week"],
            "emotional_trajectory": "Unable to determine",
            "recommendations": "Please try again later"
        }
    
    # Store in database
    try:
        conn = sqlite3.connect('diary3.db')
        cursor = conn.cursor()
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        # Convert key_events to string if it's a list
        key_events = weekly_data.get('key_events', [])
        if isinstance(key_events, list):
            key_events = json.dumps(key_events)
        
        cursor.execute(
            '''INSERT INTO weekly_summaries 
               (user_id, week_start, week_end, overall_sentiment, key_events)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, week_ago, today, weekly_data.get('overall_sentiment', 'neutral'), key_events)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error storing weekly summary: {str(e)}")
    
    return weekly_data

# Flask routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('diary3.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', 
                       (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('diary3.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                          (username, password))
            conn.commit()
            flash('Registration successful, please login')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/new_entry', methods=['GET', 'POST'])
def new_entry():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        content = request.form['content']
        result = add_entry(session['user_id'], content)
        try:
            sentiment_data = json.loads(result)
            flash(f"Your entry has been saved. Prominent emotion: {sentiment_data.get('prominent_emotion', 'neutral')}")
        except:
            flash("Your entry has been saved.")
        
        return redirect(url_for('view_entries'))
    
    return render_template('new_entry.html')

@app.route('/view_entries')
def view_entries():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('diary3.db')
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT id, entry_date, content, sentiment, sentiment_score 
           FROM entries 
           WHERE user_id = ? 
           ORDER BY entry_date DESC''',
        (session['user_id'],)
    )
    entries = cursor.fetchall()
    conn.close()
    
    return render_template('view_entries.html', entries=entries)

@app.route('/weekly_summary')
def weekly_summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get the latest weekly summary from DB or generate a new one
    conn = sqlite3.connect('diary3.db')
    cursor = conn.cursor()
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Look for any recent summary
    cursor.execute(
        '''SELECT overall_sentiment, key_events, week_end 
           FROM weekly_summaries 
           WHERE user_id = ? 
           ORDER BY week_end DESC LIMIT 1''',
        (session['user_id'],)
    )
    
    summary = cursor.fetchone()
    conn.close()
    
    # Removed hardcoded False - use proper condition
    # if summary and (today - datetime.strptime(summary[2], '%Y-%m-%d').date()).days < 1:
    if False:
        print("Using existing weekly summary")
        try:
            key_events = json.loads(summary[1]) if isinstance(summary[1], str) else summary[1]
        except json.JSONDecodeError:
            key_events = ["Error parsing events"]
            
        summary_data = {
            'overall_sentiment': summary[0],
            'key_events': key_events,
            'emotional_trajectory': "Based on your past entries",
            'recommendations': "Continue journaling regularly"
        }
        return render_template('weekly_summary.html', summary=summary_data)
    else:
        # Generate new summary
        print("Generating new weekly summary")
        summary_data = generate_weekly_summary(session['user_id'])
        
        # Format recommendations if they're a list
        if isinstance(summary_data.get('recommendations', []), list):
            # Keep as a list for the template to iterate through
            pass
        return render_template('weekly_summary.html', summary=summary_data)

if __name__ == "__main__":
    init_db()
    
    # Make sure GROQ_API_KEY is set before starting the app
    if not os.environ.get("GROQ_API_KEY"):
        print("Warning: GROQ_API_KEY environment variable is not set!")
        # You could set a default key for development here if needed
        # os.environ["GROQ_API_KEY"] = "your-development-key"
    
    app.run(debug=True)