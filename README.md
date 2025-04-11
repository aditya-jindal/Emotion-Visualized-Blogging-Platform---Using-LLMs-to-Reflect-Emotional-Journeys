# Emotion Visualized Blogging Platform - Using LLMs to Reflect Emotional Journeys

A Flask-based digital diary application that uses Large Language Models (via Groq API) to analyze your journal entries, track your emotional patterns, and provide meaningful insights about your emotional well-being over time.

## Features

- **Sentiment Analysis**: Automatically analyzes the emotional tone of each diary entry
- **Emotional Visualization**: Displays sentiment scores with color-coded indicators
- **Weekly Summaries**: Generates thoughtful summaries of your emotional trajectory
- **User Authentication**: Secure login and registration system
- **Responsive Design**: Works on desktop and mobile devices


## Prerequisites

- Python 3.8+
- Groq API key (register at [groq.com](https://groq.com))

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/Emotion-Visualized-Blogging-Platform---Using-LLMs-to-Reflect-Emotional-Journeys.git
cd Emotion-Visualized-Blogging-Platform---Using-LLMs-to-Reflect-Emotional-Journeys
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up your Groq API key
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

## Running the Application

1. Start the Flask server
```bash
python app.py
```

2. Open your browser and navigate to `http://127.0.0.1:5000`

## Usage

1. **Register/Login**: Create a new account or log in to an existing one
2. **Create Entries**: Write about your day, thoughts, and feelings
3. **View Analysis**: See the sentiment analysis of your entries
4. **Weekly Summary**: Check your emotional patterns over the past week

## How It Works

This application uses:

- **Flask**: Web framework for the application
- **SQLite**: Database to store user data and diary entries
- **LangChain & Groq**: For LLM-based sentiment analysis and summaries
- **Bootstrap**: For responsive frontend design

The app analyzes each diary entry with Groq's LLama3-70B model to:
1. Identify prominent emotions in your writing
2. Score overall sentiment (-1.0 to 1.0)
3. Generate insightful weekly summaries of emotional patterns

## Project Structure

```
├── app.py                   # Main application file
├── requirements.txt         # Python dependencies
├── diary3.db                # SQLite database file (created when app runs)
└── templates/               # HTML templates
    ├── index.html           # Home page
    ├── login.html           # Login page
    ├── register.html        # Registration page
    ├── new_entry.html       # Create new diary entry
    ├── view_entries.html    # View past entries
    └── weekly_summary.html  # Weekly emotional summary
```

## Security Notes

- This project is designed for educational purposes
- Passwords are stored in plaintext - **not recommended for production use**
- Consider implementing proper password hashing (e.g., bcrypt) for production
- Add HTTPS for secure communication in production environments

## Future Enhancements

- Emotional trend visualization with charts
- Monthly and yearly summaries
- Custom journaling prompts based on emotional patterns
- Export functionality for journal entries
- More robust security features

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Groq for providing the LLM API
- LangChain for the LLM integration framework
- Bootstrap for the frontend styling
