# GeoSudoku WebGame

A geography-themed Sudoku game built with Django and vanilla JavaScript, featuring HTML5 drag & drop functionality and geographic regions instead of traditional 3x3 boxes.

## 🌍 Features

- **Geographic Regions**: Each puzzle uses 9 geographic regions (North America, Europe, Asia, etc.) instead of traditional 3x3 boxes
- **Multiple Difficulty Levels**: Easy, Medium, Hard, and Expert puzzles
- **User Authentication**: Registration, login, and user profiles
- **Real-time Gameplay**: Drag & drop interface with instant validation
- **Progress Tracking**: Save and resume games, track scores and statistics
- **Leaderboards**: Compete with other players for the best scores
- **Achievement System**: Unlock badges and achievements
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## 🚀 Tech Stack

### Backend
- **Django 5.2.4**: Web framework
- **Django REST Framework**: API development
- **SQLite**: Development database
- **PostgreSQL**: Production database (configured)
- **Python Decouple**: Environment variable management

### Frontend
- **Django Templates**: Server-side rendering
- **Vanilla JavaScript**: Game logic and interactions
- **Bootstrap 5.3**: UI framework
- **Font Awesome**: Icons
- **HTML5 Drag & Drop API**: Game interface

## 📋 Requirements

- Python 3.8+
- Django 5.2.4
- PostgreSQL (for production)
- Modern web browser with JavaScript enabled

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd geosudoku_webgame
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///db.sqlite3

# For PostgreSQL production:
# DATABASE_URL=postgresql://username:password@localhost:5432/geosudoku_db

CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to access the application.

## 🎮 How to Play

### Basic Rules
1. Fill the 9×9 grid with numbers 1-9
2. Each row must contain all numbers 1-9
3. Each column must contain all numbers 1-9
4. Each geographic region must contain all numbers 1-9

### Game Features
- **Click to Select**: Click on any empty cell to select it
- **Number Placement**: Use the number pad or keyboard (1-9) to place numbers
- **Validation**: Invalid moves are highlighted in red
- **Hints**: Use the hint button when stuck (reduces final score)
- **Mistakes**: You're allowed 3 mistakes before game over
- **Auto-save**: Game progress is automatically saved

### Keyboard Shortcuts
- `1-9`: Place number in selected cell
- `Delete/Backspace`: Erase number from selected cell
- `H`: Get hint for selected cell
- `Ctrl+S`: Save game
- `Ctrl+Z`: Undo last move

## 🗂️ Project Structure

```
geosudoku_webgame/
├── authentication/          # User authentication app
│   ├── models.py           # Custom User model
│   ├── views.py            # Auth views (login, register, profile)
│   └── urls.py             # Auth URL patterns
├── games/                  # Game logic app
│   ├── models.py           # Puzzle, GameSession, Achievement models
│   ├── views.py            # Game views and API endpoints
│   └── urls.py             # Game URL patterns
├── api/                    # API configuration
│   └── urls.py             # API URL routing
├── geosudoku/              # Main project settings
│   ├── settings.py         # Django settings
│   └── urls.py             # Main URL configuration
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── authentication/     # Auth templates
│   └── games/              # Game templates
├── static/                 # Static files
│   ├── css/                # Custom CSS
│   └── js/                 # JavaScript files
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
└── manage.py               # Django management script
```

## 🔧 API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout

### Game API
- `GET /api/games/puzzles/` - List available puzzles
- `POST /api/games/puzzles/{id}/session/` - Start/get game session
- `POST /api/games/sessions/{id}/save/` - Save game state
- `POST /api/games/validate-move/` - Validate Sudoku move

## 🎨 Customization

### Adding New Regions
To add new geographic regions, modify the `generate_basic_puzzle` method in `games/models.py`:

```python
regions = [
    {'name': 'Your Region', 'cells': [(row, col), ...]},
    # Add more regions...
]
```

### Styling
- Modify `static/css/style.css` for custom styling
- Region colors are defined in CSS custom properties
- Bootstrap classes can be used throughout templates

## 🚀 Production Deployment

### Environment Setup
1. Set `DEBUG=False` in production
2. Configure PostgreSQL database
3. Set up static file serving
4. Configure ALLOWED_HOSTS
5. Use a production WSGI server (Gunicorn, uWSGI)

### PostgreSQL Configuration
```env
DATABASE_URL=postgresql://username:password@localhost:5432/geosudoku_db
```

### Static Files
```bash
python manage.py collectstatic
```

## 🧪 Testing

Run the Django test suite:
```bash
python manage.py test
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🐛 Known Issues

- Puzzle generation uses a simplified algorithm (suitable for demo)
- Undo functionality is basic
- Advanced Sudoku solving techniques not implemented

## 🔮 Future Enhancements

- [ ] Advanced puzzle generation algorithms
- [ ] Multiplayer functionality
- [ ] Daily challenges
- [ ] Mobile app version
- [ ] Social features (friends, sharing)
- [ ] Tournament system
- [ ] AI opponent
- [ ] Puzzle editor
- [ ] Theme customization

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Django and Django REST Framework communities
- Bootstrap team for the UI framework
- Font Awesome for icons
- Geographic inspiration from real-world regions

## 📞 Support

For support, email [your-email] or create an issue on GitHub.

---

**Happy Puzzling! 🧩🌍**